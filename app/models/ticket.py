from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from app.db.session import Base


class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in-progress"
    PROCESSED = "processed"
    DONE = "done"
    INCOMPLETE = "incomplete"


class Ticket(Base):
    """Ticket model for storing customer tickets"""
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    title = Column(String(300), nullable=True)
    
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.QUEUED, nullable=False)
    description = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    translation = Column(Text, nullable=True)
    
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="tickets")
    category = relationship("Category", back_populates="tickets")
    assignments = relationship("TicketAssignment", back_populates="ticket", cascade="all, delete-orphan")
    escalations = relationship("TicketEscalation", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Ticket(id={self.id}, email={self.email}, status={self.status})>"
