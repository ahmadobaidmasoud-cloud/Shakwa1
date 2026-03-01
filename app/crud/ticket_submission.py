from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.ticket_submission import TicketSubmission
from uuid import UUID
from datetime import datetime
from typing import Optional, List


def create_ticket_submission(
    db: Session,
    ticket_id: UUID,
    submitted_by_user_id: UUID,
    comment: str,
    submission_type: str = "employee_submission",
    attachment_url: Optional[str] = None,
    requires_changes: bool = False
) -> TicketSubmission:
    """Create a new ticket submission (comment/review)"""
    now = datetime.utcnow().isoformat()
    
    db_submission = TicketSubmission(
        ticket_id=ticket_id,
        submitted_by_user_id=submitted_by_user_id,
        submission_type=submission_type,
        comment=comment,
        attachment_url=attachment_url,
        requires_changes=requires_changes,
        created_at=now,
        updated_at=now,
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def submit_ticket_for_completion(
    db: Session,
    ticket_id: UUID,
    submitted_by_user_id: UUID,
    comment: str,
    attachment_url: Optional[str] = None
) -> dict:
    """
    Submit ticket for completion/finalization.
    Changes ticket status to 'processed' (submitted by employee for manager review).
    Creates a ticket submission record.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        return {"error": "Ticket not found"}
    
    now = datetime.utcnow().isoformat()
    
    # Create submission record
    submission = create_ticket_submission(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=submitted_by_user_id,
        comment=comment,
        submission_type="employee_submission",
        attachment_url=attachment_url
    )
    
    # Update ticket status to 'processed' (employee submitted for manager review)
    ticket.status = "processed"
    ticket.updated_at = now
    
    db.commit()
    db.refresh(ticket)

    # Stop the SLA timer since ticket moved to processed
    try:
        from app.core.redis_utils import stop_sla_timer
        stop_sla_timer(str(ticket_id))
    except Exception:
        pass  # Redis not available is non-fatal
    
    return {
        "success": True,
        "message": "Ticket submitted for completion",
        "ticket_id": str(ticket.id),
        "status": ticket.status,
        "submission_id": str(submission.id),
        "submitted_at": now,
        "submitted_by": str(submitted_by_user_id),
        "comment": comment,
        "attachment_url": attachment_url,
    }


def submit_and_resolve_ticket(
    db: Session,
    ticket_id: UUID,
    submitted_by_user_id: UUID,
    comment: str,
    attachment_url: Optional[str] = None
) -> dict:
    """
    Admin direct-resolve: submit ticket AND approve it in one step.
    Creates both an employee_submission and a manager_approval record,
    then sets the ticket status directly to 'done'.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        return {"error": "Ticket not found"}

    now = datetime.utcnow().isoformat()

    # 1. Create employee submission record
    submission = create_ticket_submission(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=submitted_by_user_id,
        comment=comment,
        submission_type="employee_submission",
        attachment_url=attachment_url,
    )

    # 2. Create auto-approval record
    create_ticket_submission(
        db=db,
        ticket_id=ticket_id,
        submitted_by_user_id=submitted_by_user_id,
        comment="Auto-approved by admin",
        submission_type="manager_approval",
    )

    # 3. Set ticket status directly to 'done'
    ticket.status = "done"
    ticket.updated_at = now

    db.commit()
    db.refresh(ticket)

    # Stop the SLA timer
    try:
        from app.core.redis_utils import stop_sla_timer
        stop_sla_timer(str(ticket_id))
    except Exception:
        pass  # Redis not available is non-fatal

    return {
        "success": True,
        "message": "Ticket resolved by admin",
        "ticket_id": str(ticket.id),
        "status": ticket.status,
        "submission_id": str(submission.id),
        "submitted_at": now,
        "submitted_by": str(submitted_by_user_id),
        "comment": comment,
        "attachment_url": attachment_url,
    }


def get_ticket_submissions(
    db: Session,
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[TicketSubmission]:
    """Get all submissions for a ticket"""
    return db.query(TicketSubmission).filter(
        TicketSubmission.ticket_id == ticket_id
    ).order_by(TicketSubmission.created_at.desc()).offset(skip).limit(limit).all()


def get_submission_by_id(
    db: Session,
    submission_id: UUID
) -> Optional[TicketSubmission]:
    """Get a specific submission"""
    return db.query(TicketSubmission).filter(
        TicketSubmission.id == submission_id
    ).first()
