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


class TicketSubmissionRequest(BaseModel):
    """Request schema for submitting a ticket for completion"""
    comment: str
    attachment_url: Optional[str] = None


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
    
    # If ticket is processed, fetch submissions
    submissions_list = None
    if ticket.status == "processed":
        from app.models.ticket_submission import TicketSubmission
        submissions = db.query(TicketSubmission).filter(
            TicketSubmission.ticket_id == ticket_id
        ).order_by(TicketSubmission.created_at.asc()).all()
        
        # Enrich with user names
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
