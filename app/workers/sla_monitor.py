"""
SLA Escalation Listener

A standalone background worker that subscribes to Redis keyspace notifications.
When a ticket SLA key expires (ticket:{id}:sla), this worker:

1. Validates the ticket is still in an active state (ASSIGNED / IN_PROGRESS).
2. Finds the current assignee and their manager.
3. Closes the current assignment, creates a new one for the manager.
4. Records the escalation in ticket_escalations.
5. Sends a notification to the manager.
6. Restarts the SLA timer for the manager.

Usage:
    python -m app.workers.sla_monitor

Prerequisites:
    Redis must have keyspace notifications enabled:
        redis-cli CONFIG SET notify-keyspace-events Ex
"""

import re
import sys
import logging
import redis
from datetime import datetime
from uuid import UUID

# Ensure the app is importable
sys.path.insert(0, ".")

from app.core.config import settings
from app.core.redis_utils import start_sla_timer
from app.db.session import SessionLocal
from app.models.configuration import Configuration  # noqa: F401 - needed for SLA lookup

# Import ALL models so SQLAlchemy relationships resolve correctly
from app.models.tenant import Tenant  # noqa: F401 - needed for Ticket.tenant relationship
from app.models.category import Category  # noqa: F401 - needed for Ticket.category relationship
from app.models.ticket_submission import TicketSubmission  # noqa: F401 - needed if relationships reference it
from app.models.notification import Notification  # noqa: F401 - needed for User.notifications relationship
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_assignment import TicketAssignment, TicketEscalation, AssignmentType
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.crud import notification as notification_crud

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sla_monitor")

# Regex to parse ticket ID from expired key
# Key format: ticket:{uuid}:sla
SLA_KEY_PATTERN = re.compile(r"^ticket:([a-f0-9\-]+):sla$")

# Active ticket statuses (if the ticket is in one of these, escalation is valid)
ESCALATABLE_STATUSES = [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]


def _get_redis_pubsub() -> redis.client.PubSub:
    """Create a Redis PubSub connection subscribed to expired key events."""
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        decode_responses=True,
    )

    # Enable keyspace notifications if not already enabled
    try:
        r.config_set("notify-keyspace-events", "Ex")
        logger.info("Redis keyspace notifications enabled (Ex)")
    except redis.ResponseError:
        logger.warning("Could not set notify-keyspace-events (may require admin privileges)")

    pubsub = r.pubsub()
    # Subscribe to expired events on the configured DB
    channel = f"__keyevent@{settings.REDIS_DB}__:expired"
    pubsub.subscribe(channel)
    logger.info(f"Subscribed to Redis channel: {channel}")
    return pubsub


def handle_sla_expiry(ticket_id_str: str):
    """
    Handle an SLA timer expiry for a given ticket.

    This runs inside a DB session and performs the full escalation flow.
    """
    db = SessionLocal()
    try:
        ticket_id = UUID(ticket_id_str)

        # ── 1. Validate ticket ──────────────────────────────────────
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found, ignoring SLA expiry")
            return

        if ticket.status not in ESCALATABLE_STATUSES:
            logger.info(
                f"Ticket {ticket_id} status is {ticket.status}, not escalatable. Ignoring."
            )
            return

        # ── 2. Get current assignment ───────────────────────────────
        current_assignment = (
            db.query(TicketAssignment)
            .filter(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.is_current == True,
            )
            .first()
        )

        if not current_assignment:
            logger.warning(f"No current assignment for ticket {ticket_id}, ignoring SLA expiry")
            return

        current_user = db.query(User).filter(User.id == current_assignment.assigned_to_user_id).first()
        if not current_user:
            logger.error(f"Assigned user {current_assignment.assigned_to_user_id} not found")
            return

        # ── 3. Find the manager ─────────────────────────────────────
        if not current_user.manager_id:
            logger.warning(
                f"User {current_user.id} ({current_user.first_name} {current_user.last_name}) "
                f"has no manager. Final escalation reached — notifying admins."
            )
            _notify_no_manager_escalation(db, ticket, current_user)
            return

        manager = db.query(User).filter(User.id == current_user.manager_id).first()
        if not manager:
            logger.error(f"Manager {current_user.manager_id} not found in database")
            return

        logger.info(
            f"Escalating ticket {ticket_id} from "
            f"{current_user.first_name} {current_user.last_name} -> "
            f"{manager.first_name} {manager.last_name}"
        )

        now = datetime.utcnow().isoformat()

        # ── 4. Close old assignment ─────────────────────────────────
        current_assignment.is_current = False
        current_assignment.completed_at = now
        current_assignment.updated_at = now

        # ── 5. Create new assignment for manager ────────────────────
        new_assignment = TicketAssignment(
            ticket_id=ticket_id,
            assigned_to_user_id=manager.id,
            assigned_by_user_id=None,  # System auto-escalation
            assignment_type=AssignmentType.AUTO_ESCALATED.value,
            is_current=True,
            assigned_at=now,
            notes=f"Auto-escalated from {current_user.first_name} {current_user.last_name} (SLA breach)",
            created_at=now,
            updated_at=now,
        )
        db.add(new_assignment)

        # ── 6. Record escalation ────────────────────────────────────
        # Determine escalation level from previous escalations
        last_escalation = (
            db.query(TicketEscalation)
            .filter(TicketEscalation.ticket_id == ticket_id)
            .order_by(TicketEscalation.escalation_level.desc())
            .first()
        )
        new_level = (last_escalation.escalation_level + 1) if last_escalation else 1

        escalation = TicketEscalation(
            ticket_id=ticket_id,
            escalated_from_user_id=current_user.id,
            escalated_to_user_id=manager.id,
            escalation_level=new_level,
            reason=f"SLA breach: ticket not resolved within SLA window",
            escalated_at=now,
            created_at=now,
        )
        db.add(escalation)

        # ── 7. Update ticket status ─────────────────────────────────
        ticket.status = TicketStatus.ASSIGNED
        ticket.updated_at = now

        db.commit()
        db.refresh(new_assignment)

        # ── 8. Send notification to manager ─────────────────────────
        notification_data = NotificationCreate(
            title="Ticket Escalated to You",
            message=(
                f"Ticket '{ticket.title or 'Untitled'}' has been escalated to you "
                f"due to SLA breach by {current_user.first_name} {current_user.last_name}."
            ),
            notification_type="ticket_assigned",
            user_id=manager.id,
            ticket_id=ticket_id,
            related_user_id=current_user.id,
        )
        notification_crud.create_notification(db, notification_data)

        # Also notify the original assignee that their ticket was escalated
        notification_data_old = NotificationCreate(
            title="Ticket Escalated",
            message=(
                f"Ticket '{ticket.title or 'Untitled'}' has been escalated to "
                f"{manager.first_name} {manager.last_name} due to SLA breach."
            ),
            notification_type="ticket_assigned",
            user_id=current_user.id,
            ticket_id=ticket_id,
            related_user_id=manager.id,
        )
        notification_crud.create_notification(db, notification_data_old)

        # ── 9. Restart SLA timer for the manager (using tenant config) ─
        try:
            from app.services.assignment import get_tenant_sla_minutes
            sla_minutes = get_tenant_sla_minutes(db, ticket.tenant_id)
            start_sla_timer(
                str(ticket_id),
                str(manager.id),
                sla_minutes,
            )
            logger.info(
                f"New SLA timer started for manager {manager.id} on ticket {ticket_id} "
                f"({sla_minutes} minutes)"
            )
        except Exception as e:
            logger.error(f"Failed to restart SLA timer: {e}")

        logger.info(
            f"Escalation complete: ticket {ticket_id} now assigned to "
            f"{manager.first_name} {manager.last_name} (level {new_level})"
        )

    except Exception as e:
        logger.exception(f"Error handling SLA expiry for ticket {ticket_id_str}: {e}")
        db.rollback()
    finally:
        db.close()


def _notify_no_manager_escalation(db, ticket: Ticket, user: User):
    """
    When there's no manager to escalate to, send a system notification
    to all admins in the same tenant.
    """
    from app.models.user import UserRole

    admins = (
        db.query(User)
        .filter(
            User.tenant_id == ticket.tenant_id,
            User.role.in_([UserRole.admin, UserRole.manager]),
            User.is_active == True,
        )
        .all()
    )

    for admin in admins:
        notification_data = NotificationCreate(
            title="Escalation Limit Reached",
            message=(
                f"Ticket '{ticket.title or 'Untitled'}' could not be escalated further. "
                f"User {user.first_name} {user.last_name} has no manager assigned. "
                f"Manual intervention required."
            ),
            notification_type="system",
            user_id=admin.id,
            ticket_id=ticket.id,
            related_user_id=user.id,
        )
        notification_crud.create_notification(db, notification_data)

    logger.info(f"Notified {len(admins)} admin(s) about final escalation for ticket {ticket.id}")


def run_listener():
    """Main loop: listen for Redis expired key events and handle SLA breaches."""
    logger.info("=" * 60)
    logger.info("SLA Escalation Monitor starting...")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
    logger.info(f"Default SLA: {settings.SLA_DEFAULT_MINUTES} minutes")
    logger.info("=" * 60)

    pubsub = _get_redis_pubsub()

    for message in pubsub.listen():
        # Skip subscribe confirmation messages
        if message["type"] != "message":
            continue

        expired_key = message.get("data", "")
        logger.debug(f"Expired key event: {expired_key}")

        # Check if this is a ticket SLA key
        match = SLA_KEY_PATTERN.match(expired_key)
        if not match:
            continue

        ticket_id_str = match.group(1)
        logger.info(f"SLA expired for ticket: {ticket_id_str}")

        try:
            handle_sla_expiry(ticket_id_str)
        except Exception as e:
            logger.exception(f"Unhandled error processing SLA expiry: {e}")


if __name__ == "__main__":
    run_listener()
