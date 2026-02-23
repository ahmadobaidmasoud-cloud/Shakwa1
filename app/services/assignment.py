"""
Least-Loaded Ticket Assignment Engine

Implements automatic ticket assignment using a load-balancing strategy:
1. Finds eligible users (correct tenant, role=user, is_accepting_tickets=True)
2. Calculates each user's active load via LEFT JOIN with ticket_assignments
3. Filters out users at or over capacity
4. Assigns to the user with the lowest active assignment count
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, not_
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_assignment import TicketAssignment, AssignmentType
from app.models.configuration import Configuration
from app.schemas.ticket_assignment import TicketAssignmentCreate
from app.schemas.notification import NotificationCreate
from app.crud import notification as notification_crud

logger = logging.getLogger(__name__)

# Statuses that count as "active" load for an agent
ACTIVE_TICKET_STATUSES = [
    TicketStatus.ASSIGNED,
    TicketStatus.IN_PROGRESS,
    TicketStatus.QUEUED,
]


def _get_candidate_users_with_load(
    db: Session,
    tenant_id: UUID,
    category_id: Optional[int] = None,
):
    """
    Query eligible users with their current active assignment count.

    Returns a list of tuples: (User, active_count)
    Sorted by active_count ascending (least loaded first).
    """

    # Subquery: count active assignments per user
    # An assignment is "active" if is_current=True AND the ticket status
    # is in ACTIVE_TICKET_STATUSES (not DONE, PROCESSED, INCOMPLETE)
    active_count_subq = (
        db.query(
            TicketAssignment.assigned_to_user_id.label("user_id"),
            func.count(TicketAssignment.id).label("active_count"),
        )
        .join(Ticket, Ticket.id == TicketAssignment.ticket_id)
        .filter(
            TicketAssignment.is_current == True,
            Ticket.status.in_(ACTIVE_TICKET_STATUSES),
        )
        .group_by(TicketAssignment.assigned_to_user_id)
        .subquery()
    )

    # Main query: eligible users LEFT JOIN active counts
    query = (
        db.query(
            User,
            func.coalesce(active_count_subq.c.active_count, 0).label("active_count"),
        )
        .outerjoin(active_count_subq, User.id == active_count_subq.c.user_id)
        .filter(
            User.tenant_id == tenant_id,
            User.role == UserRole.user,
            User.is_accepting_tickets == True,
            User.is_active == True,
        )
    )

    # Optional: filter by category if the ticket has one
    if category_id is not None:
        query = query.filter(User.category_id == category_id)

    # Exclude users at or over capacity
    query = query.filter(
        func.coalesce(active_count_subq.c.active_count, 0) < User.capacity
    )

    # Sort by least loaded first
    query = query.order_by(func.coalesce(active_count_subq.c.active_count, 0).asc())

    return query.all()


def get_tenant_sla_minutes(db: Session, tenant_id: UUID) -> int:
    """Get SLA minutes from the configurations table for a tenant.
    Falls back to settings.SLA_DEFAULT_MINUTES if not configured."""
    from app.core.config import settings
    config = db.query(Configuration).filter(
        Configuration.tenant_id == tenant_id,
        Configuration.key == "sla",
    ).first()
    if config and config.value:
        try:
            return int(config.value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid SLA value '{config.value}' for tenant {tenant_id}, using default")
    return settings.SLA_DEFAULT_MINUTES


def auto_assign_ticket(
    db: Session,
    ticket_id: UUID,
    tenant_id: UUID,
    assigned_by_user_id: Optional[UUID] = None,
    sla_minutes: Optional[int] = None,
) -> Optional[TicketAssignment]:
    """
    Automatically assign a ticket to the least-loaded eligible agent.

    Steps:
    1. Fetch the ticket and validate it's in QUEUED status.
    2. Get candidate users sorted by active load.
    3. Optionally try category-matched users first, then fall back to all.
    4. Create TicketAssignment, update ticket status, send notification.
    5. Start SLA timer in Redis.

    Returns the created TicketAssignment, or None if no eligible user found.
    """
    now = datetime.utcnow().isoformat()

    # 1. Fetch and validate ticket
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant_id,
    ).first()

    if not ticket:
        logger.warning(f"Ticket {ticket_id} not found in tenant {tenant_id}")
        return None

    # Resolve SLA minutes from tenant configuration if not provided
    if sla_minutes is None:
        sla_minutes = get_tenant_sla_minutes(db, tenant_id)

    if ticket.status != TicketStatus.QUEUED:
        logger.info(f"Ticket {ticket_id} is not QUEUED (status={ticket.status}), skipping auto-assign")
        return None

    # 2. Get candidates — strict category match when ticket has a category
    if ticket.category_id:
        candidates = _get_candidate_users_with_load(db, tenant_id, category_id=ticket.category_id)
    else:
        candidates = _get_candidate_users_with_load(db, tenant_id, category_id=None)

    if not candidates:
        logger.warning(f"No eligible agents found for ticket {ticket_id} in tenant {tenant_id}")
        return None

    # 3. Pick the best candidate (first = least loaded)
    best_user, active_count = candidates[0]
    logger.info(
        f"Auto-assigning ticket {ticket_id} to user {best_user.id} "
        f"({best_user.first_name} {best_user.last_name}) with {active_count} active tickets"
    )

    # 4. Create assignment record
    db_assignment = TicketAssignment(
        ticket_id=ticket_id,
        assigned_to_user_id=best_user.id,
        assigned_by_user_id=assigned_by_user_id,
        assignment_type=AssignmentType.AUTO_ASSIGNED.value,
        is_current=True,
        assigned_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(db_assignment)

    # 5. Update ticket status
    ticket.status = TicketStatus.ASSIGNED
    ticket.updated_at = now

    db.commit()
    db.refresh(db_assignment)

    # 6. Send notification
    notification_data = NotificationCreate(
        title="New Ticket Assigned",
        message=f"You have been automatically assigned ticket - {ticket.title or 'Untitled'}",
        notification_type="ticket_assigned",
        user_id=best_user.id,
        ticket_id=ticket_id,
        related_user_id=assigned_by_user_id,
    )
    notification_crud.create_notification(db, notification_data)

    # 7. Start SLA timer in Redis
    try:
        from app.core.redis_utils import start_sla_timer
        start_sla_timer(str(ticket_id), str(best_user.id), sla_minutes)
        logger.info(f"SLA timer started for ticket {ticket_id}: {sla_minutes} minutes")
    except Exception as e:
        logger.error(f"Failed to start SLA timer for ticket {ticket_id}: {e}")

    return db_assignment


def get_user_active_load(db: Session, user_id: UUID) -> int:
    """Get the count of active ticket assignments for a user."""
    return (
        db.query(func.count(TicketAssignment.id))
        .join(Ticket, Ticket.id == TicketAssignment.ticket_id)
        .filter(
            TicketAssignment.assigned_to_user_id == user_id,
            TicketAssignment.is_current == True,
            Ticket.status.in_(ACTIVE_TICKET_STATUSES),
        )
        .scalar()
    ) or 0
