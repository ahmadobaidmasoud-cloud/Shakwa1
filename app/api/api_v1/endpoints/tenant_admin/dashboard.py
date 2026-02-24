from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketStatus
from app.models.category import Category
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_submission import TicketSubmission

router = APIRouter()


@router.get(
    "/dashboard/stats",
    status_code=status.HTTP_200_OK,
    tags=["Admin - Dashboard"],
)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Get dashboard statistics for the current tenant.
    Returns category count, ticket counts by status, user counts by role,
    and top agents by active assignment count.
    """
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # ── Total categories ────────────────────────────────────────────
    total_categories = (
        db.query(func.count(Category.id))
        .filter(Category.tenant_id == tenant_id)
        .scalar()
    ) or 0

    # ── Total tickets ───────────────────────────────────────────────
    total_tickets = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.tenant_id == tenant_id)
        .scalar()
    ) or 0

    # ── Tickets by status ───────────────────────────────────────────
    status_rows = (
        db.query(Ticket.status, func.count(Ticket.id))
        .filter(Ticket.tenant_id == tenant_id)
        .group_by(Ticket.status)
        .all()
    )
    tickets_by_status = {s.value: 0 for s in TicketStatus}
    for row_status, count in status_rows:
        key = row_status.value if hasattr(row_status, "value") else row_status
        tickets_by_status[key] = count

    # ── Users by role ───────────────────────────────────────────────
    role_rows = (
        db.query(User.role, func.count(User.id))
        .filter(User.tenant_id == tenant_id, User.is_active == True)
        .group_by(User.role)
        .all()
    )
    users_by_role = {}
    total_users = 0
    for role, count in role_rows:
        key = role.value if hasattr(role, "value") else role
        users_by_role[key] = count
        total_users += count

    # ── Unassigned tickets ──────────────────────────────────────────
    assigned_ticket_ids = (
        db.query(TicketAssignment.ticket_id)
        .filter(TicketAssignment.is_current == True)
        .subquery()
    )
    unassigned_tickets = (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.tenant_id == tenant_id,
            ~Ticket.id.in_(db.query(assigned_ticket_ids)),
        )
        .scalar()
    ) or 0

    # ── Top agents by active assignments ────────────────────────────
    active_statuses = [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.QUEUED]
    top_agents_rows = (
        db.query(
            User.id,
            User.first_name,
            User.last_name,
            User.capacity,
            func.count(Ticket.id).label("active_tickets"),
        )
        .outerjoin(
            TicketAssignment,
            (User.id == TicketAssignment.assigned_to_user_id)
            & (TicketAssignment.is_current == True),
        )
        .outerjoin(
            Ticket,
            (Ticket.id == TicketAssignment.ticket_id)
            & (Ticket.status.in_(active_statuses)),
        )
        .filter(
            User.tenant_id == tenant_id,
            User.role == UserRole.user,
            User.is_active == True,
        )
        .group_by(User.id, User.first_name, User.last_name, User.capacity)
        .order_by(func.count(TicketAssignment.id).desc())
        .limit(10)
        .all()
    )

    top_agents = [
        {
            "id": str(row.id),
            "name": f"{row.first_name} {row.last_name}",
            "active_tickets": row.active_tickets,
            "capacity": row.capacity,
        }
        for row in top_agents_rows
    ]

    # ── Recent tickets ──────────────────────────────────────────────
    recent_tickets_rows = (
        db.query(Ticket)
        .filter(Ticket.tenant_id == tenant_id)
        .order_by(Ticket.created_at.desc())
        .limit(5)
        .all()
    )
    recent_tickets = [
        {
            "id": str(t.id),
            "title": t.title or "Untitled",
            "status": t.status.value if hasattr(t.status, "value") else t.status,
            "created_at": t.created_at,
        }
        for t in recent_tickets_rows
    ]

    # ── Employee performance ─────────────────────────────────────────
    # Employees who submitted a ticket (have a ticket_submission entry).
    # Handling time = assignment assigned_at → submission created_at.
    completed_rows = (
        db.query(
            TicketSubmission.submitted_by_user_id,
            TicketAssignment.assigned_at,
            TicketSubmission.created_at.label("submitted_at"),
        )
        .join(Ticket, Ticket.id == TicketSubmission.ticket_id)
        .join(
            TicketAssignment,
            and_(
                TicketAssignment.ticket_id == TicketSubmission.ticket_id,
                TicketAssignment.assigned_to_user_id == TicketSubmission.submitted_by_user_id,
            ),
        )
        .filter(
            Ticket.tenant_id == tenant_id,
        )
        .all()
    )

    # Group by user
    from collections import defaultdict
    perf_map = defaultdict(lambda: {"completed": 0, "total_minutes": 0.0})
    for user_id, assigned_at, submitted_at in completed_rows:
        try:
            t_start = datetime.fromisoformat(str(assigned_at))
            t_end = datetime.fromisoformat(str(submitted_at))
            diff_minutes = (t_end - t_start).total_seconds() / 60.0
        except Exception:
            diff_minutes = 0.0
        perf_map[user_id]["completed"] += 1
        perf_map[user_id]["total_minutes"] += diff_minutes

    # Resolve user names
    employee_ids = list(perf_map.keys())
    employee_performance = []
    if employee_ids:
        employees = db.query(User).filter(User.id.in_(employee_ids)).all()
        user_name_map = {u.id: f"{u.first_name} {u.last_name}".strip() for u in employees}
        for uid, data in perf_map.items():
            avg_min = data["total_minutes"] / data["completed"] if data["completed"] else 0
            employee_performance.append({
                "id": str(uid),
                "name": user_name_map.get(uid, "Unknown"),
                "completed_tickets": data["completed"],
                "avg_handling_minutes": round(avg_min, 1),
            })
        employee_performance.sort(key=lambda x: x["completed_tickets"], reverse=True)

    return {
        "total_categories": total_categories,
        "total_tickets": total_tickets,
        "total_users": total_users,
        "unassigned_tickets": unassigned_tickets,
        "tickets_by_status": tickets_by_status,
        "users_by_role": users_by_role,
        "top_agents": top_agents,
        "recent_tickets": recent_tickets,
        "employee_performance": employee_performance,
    }
