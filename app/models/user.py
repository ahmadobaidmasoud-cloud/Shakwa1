from sqlalchemy import Column, String, Boolean, DateTime, func, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from datetime import datetime
import uuid
import enum


class UserRole(str, enum.Enum):
    super_admin = "super-admin"
    admin = "admin"
    manager = "manager"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    category = relationship("Category", lazy="joined", foreign_keys=[category_id])
    assigned_tickets = relationship("TicketAssignment", foreign_keys="TicketAssignment.assigned_to_user_id", back_populates="assigned_to_user")
    assigned_by_tickets = relationship("TicketAssignment", foreign_keys="TicketAssignment.assigned_by_user_id", back_populates="assigned_by_user")
    escalated_from_tickets = relationship("TicketEscalation", foreign_keys="TicketEscalation.escalated_from_user_id", back_populates="escalated_from_user")
    escalated_to_tickets = relationship("TicketEscalation", foreign_keys="TicketEscalation.escalated_to_user_id", back_populates="escalated_to_user")

    class Config:
        from_attributes = True
