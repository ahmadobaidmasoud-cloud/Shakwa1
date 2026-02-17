from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class TicketSubmissionCreate(BaseModel):
    """Schema for creating a ticket submission"""
    comment: str
    submission_type: Optional[str] = "employee_submission"
    attachment_url: Optional[str] = None
    requires_changes: Optional[bool] = False


class TicketSubmissionOut(BaseModel):
    """Schema for returning ticket submission data"""
    id: UUID
    ticket_id: UUID
    submitted_by_user_id: UUID
    submission_type: str
    comment: str
    attachment_url: Optional[str] = None
    requires_changes: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketSubmissionWithUserOut(BaseModel):
    """Schema for returning ticket submission with user details"""
    id: UUID
    ticket_id: UUID
    submitted_by_user_id: UUID
    submitted_by_user_name: Optional[str] = None
    submission_type: str
    comment: str
    attachment_url: Optional[str] = None
    requires_changes: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
