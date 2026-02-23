from sqlalchemy import Column, String, Boolean, DateTime, func, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from datetime import datetime
import uuid
import enum


class NotificationType(str, enum.Enum):
    ticket_assigned = "ticket_assigned"
    ticket_completed = "ticket_completed"
    ticket_rejected = "ticket_rejected"
    ticket_approved = "ticket_approved"
    manager_message = "manager_message"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), default=NotificationType.system, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True)
    related_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    ticket = relationship("Ticket", foreign_keys=[ticket_id])
    related_user = relationship("User", foreign_keys=[related_user_id])

    class Config:
        from_attributes = True
