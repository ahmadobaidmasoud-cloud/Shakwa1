from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from app.db.session import Base


class AssignmentType(str, Enum):
    """Assignment type enumeration"""
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    REASSIGNED = "reassigned"
    COMPLETED = "completed"


class TicketAssignment(Base):
    """Model for tracking ticket assignments and reassignments"""
    __tablename__ = "ticket_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    assignment_type = Column(SQLEnum(AssignmentType), default=AssignmentType.ASSIGNED, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    
    assigned_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="assignments")
    assigned_to_user = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_tickets")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by_user_id], back_populates="assigned_by_tickets")

    def __repr__(self):
        return f"<TicketAssignment(id={self.id}, ticket_id={self.ticket_id}, assigned_to={self.assigned_to_user_id})>"


class TicketEscalation(Base):
    """Model for tracking ticket escalations through the hierarchy"""
    __tablename__ = "ticket_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    escalated_from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    escalated_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    escalation_level = Column(Integer, nullable=False)  # 0=employee, 1=manager, 2=senior manager, etc
    reason = Column(Text, nullable=True)
    escalated_at = Column(String, nullable=False)
    
    created_at = Column(String, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="escalations")
    escalated_from_user = relationship("User", foreign_keys=[escalated_from_user_id], back_populates="escalated_from_tickets")
    escalated_to_user = relationship("User", foreign_keys=[escalated_to_user_id], back_populates="escalated_to_tickets")

    def __repr__(self):
        return f"<TicketEscalation(id={self.id}, ticket_id={self.ticket_id}, level={self.escalation_level})>"
