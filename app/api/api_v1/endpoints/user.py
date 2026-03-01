from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.category import Category
from app.schemas.ticket import TicketOut, TicketStatus, TicketDetailOut, CurrentAssignmentBrief, CurrentAssignmentDetailed, APIResponse, TicketSubmissionBrief
from app.schemas.ticket_submission import TicketSubmissionOut, TicketSubmissionWithUserOut
from app.crud import ticket as crud_ticket
from app.crud import ticket_assignment as crud_assignment
from app.crud import ticket_submission as crud_submission
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get(
    "/my-stats",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
    },
)
async def get_my_ticket_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get performance KPIs for the currently logged-in user:
    total_assigned, completed_tickets, completed_on_time, avg_handling_minutes.
    """
    from sqlalchemy import func, and_
    from datetime import datetime
    from app.models.ticket_submission import TicketSubmission

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    uid = current_user.id
    tenant_id = current_user.tenant_id

    # Total assignments for this user
    total_assigned = (
        db.query(func.count(TicketAssignment.id))
        .join(Ticket, Ticket.id == TicketAssignment.ticket_id)
        .filter(
            TicketAssignment.assigned_to_user_id == uid,
            Ticket.tenant_id == tenant_id,
        )
        .scalar()
    ) or 0

    # SLA threshold
    try:
        from app.services.assignment import get_tenant_sla_minutes
        sla_minutes = get_tenant_sla_minutes(db, tenant_id)
    except Exception:
        sla_minutes = 60

    # Completed submissions with handling time
    completed_rows = (
        db.query(
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
            TicketSubmission.submitted_by_user_id == uid,
            Ticket.tenant_id == tenant_id,
            TicketSubmission.submission_type == "employee_submission",
        )
        .all()
    )

    completed_tickets = 0
    completed_on_time = 0
    total_minutes = 0.0
    for assigned_at, submitted_at in completed_rows:
        try:
            t_start = datetime.fromisoformat(str(assigned_at))
            t_end = datetime.fromisoformat(str(submitted_at))
            diff_minutes = (t_end - t_start).total_seconds() / 60.0
        except Exception:
            diff_minutes = 0.0
        completed_tickets += 1
        total_minutes += diff_minutes
        if diff_minutes <= sla_minutes:
            completed_on_time += 1

    avg_handling = round(total_minutes / completed_tickets, 1) if completed_tickets else 0

    return {
        "total_assigned": total_assigned,
        "completed_tickets": completed_tickets,
        "completed_on_time": completed_on_time,
        "avg_handling_minutes": avg_handling,
    }


@router.get(
    "/members",
    status_code=status.HTTP_200_OK,
    tags=["User - Members"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
    },
)
async def get_managed_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the list of users directly managed by the current manager,
    including each member's currently assigned ticket count and capacity.
    Only accessible by users with role 'manager'.
    """
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value not in ["manager", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can access this endpoint",
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Get direct reports of this manager
    direct_reports = db.query(User).filter(
        User.manager_id == current_user.id,
        User.tenant_id == current_user.tenant_id,
    ).all()

    result = []
    for member in direct_reports:
        # Count only ACTIVE tickets (not processed/done) — these consume capacity
        assigned_ticket_count = (
            db.query(TicketAssignment)
            .join(Ticket, TicketAssignment.ticket_id == Ticket.id)
            .filter(
                TicketAssignment.assigned_to_user_id == member.id,
                TicketAssignment.is_current == True,
                Ticket.status.notin_(["processed", "done", "incomplete"]),
            )
            .count()
        )

        result.append({
            "id": str(member.id),
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "role": member.role.value if hasattr(member.role, "value") else str(member.role),
            "is_active": member.is_active,
            "capacity": member.capacity,
            "assigned_tickets_count": assigned_ticket_count,
        })

    return result



class TicketSubmissionRequest(BaseModel):
    """Request schema for submitting a ticket for completion"""
    comment: str
    attachment_url: Optional[str] = None


class ApproveTicketRequest(BaseModel):
    """Request schema for manager ticket approval (comment is optional)"""
    comment: Optional[str] = None



@router.post(
    "/tickets/{ticket_id}/approve",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
        404: {"model": APIResponse, "description": "Ticket not found"},
        400: {"model": APIResponse, "description": "Ticket not in processable state"},
    },
)
async def approve_ticket(
    ticket_id: UUID,
    body: ApproveTicketRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manager approves a processed ticket submitted by one of their team members.
    Sets ticket status to 'done' and records a manager_approval submission.
    Only callable by managers, and only for tickets assigned to their direct reports.
    """
    from datetime import datetime

    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value not in ["manager", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can approve tickets",
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Fetch the ticket
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == current_user.tenant_id,
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if ticket.status.value not in ["processed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket must be in 'processed' status to approve. Current status: {ticket.status.value}",
        )

    # Verify the ticket is currently assigned to a direct report of this manager
    current_assignment = db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id,
        TicketAssignment.is_current == True,
    ).first()

    if not current_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No current assignment found for this ticket",
        )

    direct_report_ids = _get_direct_report_ids(db, current_user.id)
    if role_value != "admin" and current_assignment.assigned_to_user_id not in direct_report_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only approve tickets assigned to your direct reports",
        )

    now = datetime.utcnow().isoformat()

    # Record approval as a submission entry
    from app.crud import ticket_submission as crud_submission
    approval_comment = (body.comment.strip() if body and body.comment and body.comment.strip() else "Approved by manager")
    crud_submission.create_ticket_submission(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=current_user.id,
        comment=approval_comment,
        submission_type="manager_approval",
    )

    # Mark ticket as done
    ticket.status = "done"
    ticket.updated_at = now
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": "Ticket approved",
        "ticket_id": str(ticket.id),
        "status": ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        "approved_by": str(current_user.id),
        "approved_at": now,
    }


def _get_direct_report_ids(db: Session, manager_id: UUID) -> list:
    """Get IDs of users directly reporting to this manager (one level only)."""
    reports = db.query(User).filter(User.manager_id == manager_id).all()
    return [r.id for r in reports]


@router.post(
    "/tickets/{ticket_id}/submit",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def submit_ticket_for_completion(
    ticket_id: UUID,
    submission: TicketSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a ticket for completion (finalization).
    User/employee submits ticket indicating work is done.
    Manager will then review and mark as complete.
    Ticket status changes to 'processed'.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket exists and belongs to tenant
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == current_user.tenant_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Call CRUD function to submit ticket
    result = crud_submission.submit_ticket_for_completion(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=current_user.id,
        comment=submission.comment,
        attachment_url=submission.attachment_url,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return result


@router.post(
    "/tickets/{ticket_id}/submit-and-resolve",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized — admin only"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def submit_and_resolve_ticket(
    ticket_id: UUID,
    submission: TicketSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin-only: submit ticket AND resolve (approve) it in one step.
    Skips the 'processed' review queue since Admin is the highest authority.
    Sets ticket status directly to 'done'.
    """
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can use the submit-and-resolve action",
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket exists and belongs to tenant
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == current_user.tenant_id,
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    result = crud_submission.submit_and_resolve_ticket(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=current_user.id,
        comment=submission.comment,
        attachment_url=submission.attachment_url,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return result


@router.get(
    "/tickets/{ticket_id}/submissions",
    response_model=List[TicketSubmissionWithUserOut],
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def get_ticket_submissions(
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all submissions/comments for a ticket.
    Includes both employee submissions and manager reviews.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket exists and belongs to tenant
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == current_user.tenant_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Get submissions
    from app.models.ticket_submission import TicketSubmission
    submissions = db.query(TicketSubmission).filter(
        TicketSubmission.ticket_id == ticket_id
    ).order_by(TicketSubmission.created_at.desc()).offset(skip).limit(limit).all()

    # Enrich with user names
    from app.models.user import User as UserModel
    result = []
    for submission in submissions:
        user = db.query(UserModel).filter(UserModel.id == submission.submitted_by_user_id).first()
        user_name = f"{user.first_name} {user.last_name}" if user else "Unknown"
        
        result.append(TicketSubmissionWithUserOut(
            id=submission.id,
            ticket_id=submission.ticket_id,
            submitted_by_user_id=submission.submitted_by_user_id,
            submitted_by_user_name=user_name,
            submission_type=submission.submission_type,
            comment=submission.comment,
            attachment_url=submission.attachment_url,
            requires_changes=submission.requires_changes,
            created_at=str(submission.created_at),
            updated_at=str(submission.updated_at),
        ))

    return result


@router.get(
    "/tickets",
    response_model=List[TicketOut],
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized"},
    },
)
async def get_assigned_tickets(
    skip: int = 0,
    limit: int = 100,
    status_filter: TicketStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get tickets assigned to current user or their team members.
    
    - **Employee/User**: Gets tickets directly assigned to them
    - **Manager**: Gets tickets assigned to them AND their team members
    - Both support status filtering (queued, assigned, in-progress, processed, done, incomplete)
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Get the current user's role
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    # Get list of user IDs to filter tickets for
    user_ids = [current_user.id]
    
    # If user is a manager, also include their team members
    if role_value in ["manager", "admin"]:
        team_members = _get_team_members(db, current_user.id)
        user_ids.extend(team_members)

    # Step 1: Get paginated ticket IDs assigned to user/team
    base_query = db.query(TicketAssignment.ticket_id).filter(
        TicketAssignment.assigned_to_user_id.in_(user_ids),
        TicketAssignment.is_current == True
    )
    
    if status_filter:
        base_query = base_query.join(Ticket).filter(Ticket.status == status_filter)
    
    paginated_ticket_ids = base_query.offset(skip).limit(limit).all()
    ticket_ids = [t[0] for t in paginated_ticket_ids]

    # Step 2: Single optimized query to get all tickets with category and user data
    if ticket_ids:
        tickets_with_data = db.query(
            Ticket,
            TicketAssignment,
            Category,
            User
        ).filter(
            Ticket.id.in_(ticket_ids),
            Ticket.tenant_id == current_user.tenant_id
        ).outerjoin(
            TicketAssignment, (Ticket.id == TicketAssignment.ticket_id) & (TicketAssignment.is_current == True)
        ).outerjoin(
            Category, Ticket.category_id == Category.id
        ).outerjoin(
            User, TicketAssignment.assigned_to_user_id == User.id
        ).all()
    else:
        tickets_with_data = []

    # Build results from the joined query
    result = []
    for ticket, assignment, category, assigned_user in tickets_with_data:
        assigned_user_name = f"{assigned_user.first_name} {assigned_user.last_name}".strip() if assigned_user else None
        
        ticket_out = TicketOut(
            id=ticket.id,
            tenant_id=ticket.tenant_id,
            category_id=ticket.category_id,
            category_name=category.name if category else None,
            first_name=ticket.first_name,
            last_name=ticket.last_name,
            email=ticket.email,
            phone=ticket.phone,
            title=ticket.title,
            status=ticket.status,
            description=ticket.description,
            summary=ticket.summary,
            translation=ticket.translation,
            current_assignment=CurrentAssignmentBrief(
                assigned_to_user_id=assignment.assigned_to_user_id,
                assigned_to_user_name=assigned_user_name,
                assignment_type=assignment.assignment_type,
                assigned_at=str(assignment.assigned_at),
            ) if assignment else None,
            created_at=str(ticket.created_at),
            updated_at=str(ticket.updated_at),
        )
        result.append(ticket_out)
    
    return result


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailOut,
    status_code=status.HTTP_200_OK,
    tags=["User - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized to view this ticket"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def get_assigned_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details for a specific ticket.
    
    Users can view tickets:
    - Directly assigned to them
    - Assigned to their team members (if manager)
    - Unassigned tickets (available to all users in tenant)
    - Within their tenant
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Get the current user's role
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    # Build list of authorized user IDs
    authorized_user_ids = [current_user.id]
    if role_value in ["manager", "admin"]:
        team_members = _get_team_members(db, current_user.id)
        authorized_user_ids.extend(team_members)

    # Query to get ticket with optional assignment, category, and user data
    result = db.query(
        Ticket,
        TicketAssignment,
        Category,
        User
    ).outerjoin(
        TicketAssignment, (Ticket.id == TicketAssignment.ticket_id) & (TicketAssignment.is_current == True)
    ).outerjoin(
        Category, Ticket.category_id == Category.id
    ).outerjoin(
        User, TicketAssignment.assigned_to_user_id == User.id
    ).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == current_user.tenant_id
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    ticket, assignment, category, assigned_user = result
    
    # Authorization check: 
    # - Allow if ticket is assigned to current user or their team
    # - Allow if ticket is unassigned (no assignment)
    if assignment and assignment.assigned_to_user_id not in authorized_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this ticket",
        )
    
    assigned_user_name = f"{assigned_user.first_name} {assigned_user.last_name}".strip() if assigned_user else None
    
    # Always fetch submissions when they exist
    from app.models.ticket_submission import TicketSubmission
    submissions_list = None
    submissions = db.query(TicketSubmission).filter(
        TicketSubmission.ticket_id == ticket_id
    ).order_by(TicketSubmission.created_at.asc()).all()
    
    if submissions:
        submissions_list = []
        for submission in submissions:
            submitter = db.query(User).filter(User.id == submission.submitted_by_user_id).first()
            submitter_name = f"{submitter.first_name} {submitter.last_name}" if submitter else "Unknown"
            
            submissions_list.append(TicketSubmissionBrief(
                id=submission.id,
                submitted_by_user_name=submitter_name,
                submission_type=submission.submission_type,
                comment=submission.comment,
                attachment_url=submission.attachment_url,
                requires_changes=submission.requires_changes,
                created_at=str(submission.created_at),
            ))
    
    return TicketDetailOut(
        id=ticket.id,
        tenant_id=ticket.tenant_id,
        category_id=ticket.category_id,
        category_name=category.name if category else None,
        first_name=ticket.first_name,
        last_name=ticket.last_name,
        email=ticket.email,
        phone=ticket.phone,
        title=ticket.title,
        status=ticket.status,
        description=ticket.description,
        summary=ticket.summary,
        translation=ticket.translation,
        current_assignment=CurrentAssignmentDetailed(
            id=assignment.id,
            assigned_to_user_id=assignment.assigned_to_user_id,
            assigned_to_user_name=assigned_user_name,
            assignment_type=assignment.assignment_type,
            assigned_at=str(assignment.assigned_at),
        ) if assignment else None,
        submissions=submissions_list,
        created_at=str(ticket.created_at),
        updated_at=str(ticket.updated_at),
    )



def _get_team_members(db: Session, manager_id: UUID) -> List[UUID]:
    """
    Recursively get all team members under a manager.
    Handles multi-level manager hierarchy: manager -> manager -> employee
    """
    from app.crud import user as crud_user
    
    team_members = []
    
    # Get all direct reports (employees and managers reporting to this manager)
    direct_reports = db.query(User).filter(User.manager_id == manager_id).all()
    
    for report in direct_reports:
        team_members.append(report.id)
        
        # If this report is also a manager, recursively get their team members
        role_value = report.role.value if hasattr(report.role, "value") else str(report.role)
        if role_value == "manager":
            team_members.extend(_get_team_members(db, report.id))
    
    return team_members
