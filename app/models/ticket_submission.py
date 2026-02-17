from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.session import Base


class TicketSubmission(Base):
    __tablename__ = "ticket_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, index=True)
    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Type of submission: 'employee_submission', 'manager_review', 'note', 'approval', 'rejection'
    submission_type = Column(String(50), default="employee_submission", nullable=False)
    
    comment = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    
    # Manager can require changes - flag this submission as review feedback
    requires_changes = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TicketSubmission(id={self.id}, ticket_id={self.ticket_id}, type={self.submission_type})>"
