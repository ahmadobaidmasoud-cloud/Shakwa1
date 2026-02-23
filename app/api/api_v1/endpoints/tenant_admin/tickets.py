from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.category import Category
from app.models.ticket_submission import TicketSubmission
from app.schemas.ticket import TicketOut, TicketDetailOut, TicketUpdate, TicketStatus, TicketAssignmentHistoryItem, CurrentAssignmentBrief, CurrentAssignmentDetailed, APIResponse, TicketSubmissionBrief
from app.schemas.ticket_assignment import AssignTicketRequest, TicketAssignmentOut
from app.crud import ticket as crud_ticket
from app.crud import ticket_assignment as crud_assignment
from app.services.assignment import auto_assign_ticket
from app.core.config import settings

router = APIRouter()


@router.get(
    "/tickets",
    response_model=List[TicketOut],
    status_code=status.HTTP_200_OK,
    tags=["Admin - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
    },
)
async def list_tenant_tickets(
    skip: int = 0,
    limit: int = 100,
    status_filter: TicketStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get all tickets for the current tenant (Admin only). Includes both assigned and unassigned tickets."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Get all tickets (assigned and unassigned) with pagination
    tickets_query = db.query(Ticket).filter(
        Ticket.tenant_id == current_user.tenant_id
    )
    
    if status_filter:
        tickets_query = tickets_query.filter(Ticket.status == status_filter)
    
    tickets = tickets_query.offset(skip).limit(limit).all()
    ticket_ids = [t.id for t in tickets]
    
    # Single optimized query: get all tickets with optional assignment, category, and user data
    if ticket_ids:
        tickets_with_data = db.query(
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
            Ticket.id.in_(ticket_ids),
            Ticket.tenant_id == current_user.tenant_id
        )
        
        if status_filter:
            tickets_with_data = tickets_with_data.filter(Ticket.status == status_filter)
        
        tickets_with_data = tickets_with_data.all()
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
    tags=["Admin - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def get_tenant_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a specific ticket from the current tenant with full assignment details (Admin only). Includes unassigned tickets."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

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
    assigned_user_name = f"{assigned_user.first_name} {assigned_user.last_name}".strip() if assigned_user else None
    
    current_assignment = CurrentAssignmentDetailed(
        id=assignment.id,
        assigned_to_user_id=assignment.assigned_to_user_id,
        assigned_to_user_name=assigned_user_name,
        assigned_by_user_id=assignment.assigned_by_user_id,
        assigned_by_user_name=None,  # Would need additional join if needed
        assignment_type=assignment.assignment_type,
        assigned_at=str(assignment.assigned_at),
        notes=assignment.notes,
    ) if assignment else None
    
    # Always fetch submissions when they exist
    submissions_list = None
    submissions = db.query(TicketSubmission).filter(
        TicketSubmission.ticket_id == ticket_id
    ).order_by(TicketSubmission.created_at.asc()).all()
    
    if submissions:
        submissions_list = []
        for submission in submissions:
            # Get submitter user name
            submitter_user = db.query(User).filter(User.id == submission.submitted_by_user_id).first()
            submitter_name = f"{submitter_user.first_name} {submitter_user.last_name}".strip() if submitter_user else "Unknown"
            
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
        current_assignment=current_assignment,
        created_at=str(ticket.created_at),
        updated_at=str(ticket.updated_at),
        submissions=submissions_list,
    )


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    status_code=status.HTTP_200_OK,
    tags=["Admin - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def update_tenant_ticket(
    ticket_id: UUID,
    ticket_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update a ticket (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    ticket = crud_ticket.update_ticket(db, ticket_id, current_user.tenant_id, ticket_data)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Stop SLA timer when ticket moves to a terminal/processed status
    if ticket_data.status in [TicketStatus.DONE, TicketStatus.PROCESSED, TicketStatus.INCOMPLETE]:
        try:
            from app.core.redis_utils import stop_sla_timer
            stop_sla_timer(str(ticket_id))
        except Exception:
            pass  # Redis not available is non-fatal

    return ticket


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def delete_tenant_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete a ticket (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    success = crud_ticket.delete_ticket(db, ticket_id, current_user.tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return None


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=TicketAssignmentOut,
    status_code=status.HTTP_200_OK,
    tags=["Admin - Tickets"],
    responses={
        400: {"model": APIResponse, "description": "Invalid request"},
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket or user not found"},
    },
)
async def assign_ticket(
    ticket_id: UUID,
    assignment_data: AssignTicketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Assign a ticket to an employee (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket belongs to the tenant
    ticket = crud_ticket.get_ticket_by_id_in_tenant(db, ticket_id, current_user.tenant_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Verify the user being assigned to exists, belongs to the tenant, and is an employee
    assigned_user = db.query(User).filter(
        User.id == assignment_data.assigned_to_user_id,
        User.tenant_id == current_user.tenant_id,
        User.role == "user"  # Only employees can be assigned tickets
    ).first()
    
    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in tenant or user is not an employee",
        )

    # Create the assignment (this will close any current assignment)
    assignment = crud_assignment.reassign_ticket(
        db,
        ticket_id=ticket_id,
        new_assigned_to_user_id=assignment_data.assigned_to_user_id,
        assigned_by_user_id=current_user.id,
        assignment_type="assigned",
        notes=assignment_data.notes
    )

    # Start SLA timer for the manual assignment
    try:
        from app.core.redis_utils import start_sla_timer
        from app.services.assignment import get_tenant_sla_minutes
        sla_minutes = get_tenant_sla_minutes(db, current_user.tenant_id)
        start_sla_timer(str(ticket_id), str(assignment_data.assigned_to_user_id), sla_minutes)
    except Exception:
        pass  # Redis not available is non-fatal

    return assignment


@router.get(
    "/tickets/{ticket_id}/assignments",
    response_model=List[TicketAssignmentHistoryItem],
    status_code=status.HTTP_200_OK,
    tags=["Admin - Tickets"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def get_ticket_assignment_history(
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get assignment history for a ticket (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket belongs to the tenant
    ticket = crud_ticket.get_ticket_by_id_in_tenant(db, ticket_id, current_user.tenant_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Get assignment history with user details
    history = crud_assignment.get_assignment_history_with_users(db, ticket_id, skip, limit)
    
    # Convert dict history to TicketAssignmentHistoryItem objects
    result = []
    for item in history:
        result.append(TicketAssignmentHistoryItem(
            id=item.get("id"),
            assigned_to_user_id=item.get("assigned_to_user_id"),
            assigned_to_user_name=item.get("assigned_to_user_name"),
            assigned_by_user_id=item.get("assigned_by_user_id"),
            assigned_by_user_name=item.get("assigned_by_user_name"),
            assignment_type=item.get("assignment_type"),
            is_current=item.get("is_current"),
            assigned_at=item.get("assigned_at"),
            completed_at=item.get("completed_at"),
            notes=item.get("notes"),
        ))
    
    return result


@router.post(
    "/tickets/{ticket_id}/auto-assign",
    response_model=TicketAssignmentOut,
    status_code=status.HTTP_200_OK,
    tags=["Admin - Tickets"],
    responses={
        400: {"model": APIResponse, "description": "No eligible agents or ticket not queued"},
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Ticket not found"},
    },
)
async def auto_assign_ticket_endpoint(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Automatically assign a ticket to the least-loaded eligible agent (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify ticket belongs to the tenant
    ticket = crud_ticket.get_ticket_by_id_in_tenant(db, ticket_id, current_user.tenant_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    assignment = auto_assign_ticket(
        db=db,
        ticket_id=ticket_id,
        tenant_id=current_user.tenant_id,
        assigned_by_user_id=current_user.id,
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No eligible agents found or ticket is not in queued status",
        )

    return assignment
