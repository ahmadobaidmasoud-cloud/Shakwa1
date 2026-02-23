from sqlalchemy.orm import Session
from app.models.ticket_assignment import TicketAssignment, TicketEscalation
from app.models.ticket import Ticket
from app.schemas.ticket_assignment import TicketAssignmentCreate, TicketAssignmentUpdate, TicketEscalationCreate
from app.schemas.notification import NotificationCreate
from app.crud import notification as notification_crud
from uuid import UUID
from typing import Optional, List
from datetime import datetime


def create_ticket_assignment(
    db: Session,
    assignment_data: TicketAssignmentCreate
) -> TicketAssignment:
    """Create a new ticket assignment and send notification to assigned user"""
    now = datetime.utcnow().isoformat()
    db_assignment = TicketAssignment(
        ticket_id=assignment_data.ticket_id,
        assigned_to_user_id=assignment_data.assigned_to_user_id,
        assigned_by_user_id=assignment_data.assigned_by_user_id,
        assignment_type=assignment_data.assignment_type,
        is_current=True,
        assigned_at=now,
        notes=assignment_data.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(db_assignment)
    
    # Update ticket status to "assigned"
    ticket = db.query(Ticket).filter(Ticket.id == assignment_data.ticket_id).first()
    if ticket:
        ticket.status = "assigned"
        ticket.updated_at = now
    
    db.commit()
    db.refresh(db_assignment)
    
    # Send notification to assigned user
    if ticket:
        notification_data = NotificationCreate(
            title="New Ticket Assigned",
            message=f"You have been assigned ticket - {ticket.title}",
            notification_type="ticket_assigned",
            user_id=assignment_data.assigned_to_user_id,
            ticket_id=assignment_data.ticket_id,
            related_user_id=assignment_data.assigned_by_user_id,
        )
        notification_crud.create_notification(db, notification_data)
    
    return db_assignment


def get_current_assignment(
    db: Session,
    ticket_id: UUID
) -> Optional[TicketAssignment]:
    """Get the current assignment for a ticket"""
    return db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id,
        TicketAssignment.is_current == True
    ).first()


def get_assignments_by_ticket(
    db: Session,
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[TicketAssignment]:
    """Get all assignments for a ticket"""
    return db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id
    ).order_by(TicketAssignment.assigned_at.desc()).offset(skip).limit(limit).all()


def get_assignments_by_user(
    db: Session,
    user_id: UUID,
    is_current: bool = True,
    skip: int = 0,
    limit: int = 100
) -> List[TicketAssignment]:
    """Get assignments for a user"""
    query = db.query(TicketAssignment).filter(
        TicketAssignment.assigned_to_user_id == user_id
    )
    if is_current:
        query = query.filter(TicketAssignment.is_current == True)
    
    return query.offset(skip).limit(limit).all()


def update_assignment(
    db: Session,
    assignment_id: UUID,
    assignment_data: TicketAssignmentUpdate
) -> Optional[TicketAssignment]:
    """Update an assignment"""
    assignment = db.query(TicketAssignment).filter(
        TicketAssignment.id == assignment_id
    ).first()
    
    if not assignment:
        return None
    
    update_data = assignment_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    for field, value in update_data.items():
        setattr(assignment, field, value)
    
    db.commit()
    db.refresh(assignment)
    return assignment


def close_current_assignment(
    db: Session,
    ticket_id: UUID,
    completed_at: Optional[str] = None
) -> Optional[TicketAssignment]:
    """Close the current assignment for a ticket"""
    assignment = get_current_assignment(db, ticket_id)
    if not assignment:
        return None
    
    assignment.is_current = False
    assignment.completed_at = completed_at or datetime.utcnow().isoformat()
    assignment.updated_at = datetime.utcnow().isoformat()
    
    db.commit()
    db.refresh(assignment)
    return assignment


def reassign_ticket(
    db: Session,
    ticket_id: UUID,
    new_assigned_to_user_id: UUID,
    assigned_by_user_id: UUID,
    assignment_type: str = "reassigned",
    notes: Optional[str] = None
) -> TicketAssignment:
    """Reassign a ticket (close current assignment and create new one)"""
    # Close current assignment
    close_current_assignment(db, ticket_id)
    
    # Create new assignment
    assignment_data = TicketAssignmentCreate(
        ticket_id=ticket_id,
        assigned_to_user_id=new_assigned_to_user_id,
        assigned_by_user_id=assigned_by_user_id,
        assignment_type=assignment_type,
        notes=notes
    )
    
    return create_ticket_assignment(db, assignment_data)


# Escalation functions

def create_ticket_escalation(
    db: Session,
    escalation_data: TicketEscalationCreate
) -> TicketEscalation:
    """Create a ticket escalation record"""
    now = datetime.utcnow().isoformat()
    db_escalation = TicketEscalation(
        ticket_id=escalation_data.ticket_id,
        escalated_from_user_id=escalation_data.escalated_from_user_id,
        escalated_to_user_id=escalation_data.escalated_to_user_id,
        escalation_level=escalation_data.escalation_level,
        reason=escalation_data.reason,
        escalated_at=now,
        created_at=now,
    )
    db.add(db_escalation)
    db.commit()
    db.refresh(db_escalation)
    return db_escalation


def get_escalations_by_ticket(
    db: Session,
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[TicketEscalation]:
    """Get all escalations for a ticket"""
    return db.query(TicketEscalation).filter(
        TicketEscalation.ticket_id == ticket_id
    ).order_by(TicketEscalation.escalated_at.desc()).offset(skip).limit(limit).all()


def get_last_escalation(
    db: Session,
    ticket_id: UUID
) -> Optional[TicketEscalation]:
    """Get the most recent escalation for a ticket"""
    return db.query(TicketEscalation).filter(
        TicketEscalation.ticket_id == ticket_id
    ).order_by(TicketEscalation.escalated_at.desc()).first()


def get_current_assignment_with_user(db: Session, ticket_id: UUID) -> Optional[dict]:
    """Get current assignment for a ticket with user details"""
    from app.models.user import User
    
    assignment = db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id,
        TicketAssignment.is_current == True
    ).first()
    
    if not assignment:
        return None
    
    # Get assigned to user details
    assigned_to_user = db.query(User).filter(User.id == assignment.assigned_to_user_id).first()
    assigned_by_user = None
    
    if assignment.assigned_by_user_id:
        assigned_by_user = db.query(User).filter(User.id == assignment.assigned_by_user_id).first()
    
    return {
        "id": str(assignment.id),
        "assigned_to_user_id": str(assignment.assigned_to_user_id),
        "assigned_to_user_name": f"{assigned_to_user.first_name} {assigned_to_user.last_name}" if assigned_to_user else "Unknown",
        "assigned_by_user_id": str(assignment.assigned_by_user_id) if assignment.assigned_by_user_id else None,
        "assigned_by_user_name": f"{assigned_by_user.first_name} {assigned_by_user.last_name}" if assigned_by_user else None,
        "assignment_type": assignment.assignment_type,
        "assigned_at": assignment.assigned_at,
        "notes": assignment.notes,
    }


def get_assignment_history_with_users(
    db: Session,
    ticket_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[dict]:
    """Get assignment history for a ticket with user details"""
    from app.models.user import User
    
    assignments = db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id
    ).order_by(TicketAssignment.assigned_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for assignment in assignments:
        assigned_to_user = db.query(User).filter(User.id == assignment.assigned_to_user_id).first()
        assigned_by_user = None
        
        if assignment.assigned_by_user_id:
            assigned_by_user = db.query(User).filter(User.id == assignment.assigned_by_user_id).first()
        
        result.append({
            "id": str(assignment.id),
            "assigned_to_user_id": str(assignment.assigned_to_user_id),
            "assigned_to_user_name": f"{assigned_to_user.first_name} {assigned_to_user.last_name}" if assigned_to_user else "Unknown",
            "assigned_by_user_id": str(assignment.assigned_by_user_id) if assignment.assigned_by_user_id else None,
            "assigned_by_user_name": f"{assigned_by_user.first_name} {assigned_by_user.last_name}" if assigned_by_user else None,
            "assignment_type": assignment.assignment_type,
            "is_current": assignment.is_current,
            "assigned_at": assignment.assigned_at,
            "completed_at": assignment.completed_at,
            "notes": assignment.notes,
        })
    
    return result
