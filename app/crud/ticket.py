from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate
from uuid import UUID
from typing import Optional, List
from datetime import datetime


def create_ticket(db: Session, tenant_id: UUID, ticket_data: TicketCreate) -> Ticket:
    """Create a new ticket"""
    now = datetime.utcnow().isoformat()
    db_ticket = Ticket(
        tenant_id=tenant_id,
        first_name=ticket_data.first_name,
        last_name=ticket_data.last_name,
        email=ticket_data.email,
        phone=ticket_data.phone,
        description=ticket_data.description,
        status=TicketStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def get_ticket_by_id(db: Session, ticket_id: UUID) -> Optional[Ticket]:
    """Get a ticket by ID"""
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def get_ticket_by_id_in_tenant(db: Session, ticket_id: UUID, tenant_id: UUID) -> Optional[Ticket]:
    """Get a ticket by ID within a tenant"""
    return db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant_id
    ).first()


def get_tickets_by_tenant(
    db: Session,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TicketStatus] = None
) -> List[Ticket]:
    """Get all tickets for a tenant with optional status filter"""
    query = db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
    
    if status:
        query = query.filter(Ticket.status == status)
    
    return query.offset(skip).limit(limit).all()


def update_ticket(
    db: Session,
    ticket_id: UUID,
    tenant_id: UUID,
    ticket_data: TicketUpdate
) -> Optional[Ticket]:
    """Update a ticket"""
    ticket = get_ticket_by_id_in_tenant(db, ticket_id, tenant_id)
    if not ticket:
        return None
    
    update_data = ticket_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    for field, value in update_data.items():
        setattr(ticket, field, value)
    
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: UUID, tenant_id: UUID) -> bool:
    """Delete a ticket"""
    ticket = get_ticket_by_id_in_tenant(db, ticket_id, tenant_id)
    if not ticket:
        return False
    
    db.delete(ticket)
    db.commit()
    return True


def count_tickets_by_tenant(db: Session, tenant_id: UUID) -> int:
    """Get count of tickets for a tenant"""
    return db.query(Ticket).filter(Ticket.tenant_id == tenant_id).count()


def count_tickets_by_status(db: Session, tenant_id: UUID, status: TicketStatus) -> int:
    """Get count of tickets for a tenant by status"""
    return db.query(Ticket).filter(
        Ticket.tenant_id == tenant_id,
        Ticket.status == status
    ).count()
