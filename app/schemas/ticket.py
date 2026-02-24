from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from uuid import UUID
from enum import Enum
from datetime import datetime


class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in-progress"
    PROCESSED = "processed"
    DONE = "done"
    INCOMPLETE = "incomplete"


class TicketCreate(BaseModel):
    """Schema for creating a new ticket (public)"""
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    description: str = Field(..., min_length=1)

    @field_validator('first_name', 'last_name', 'phone', mode='before')
    @classmethod
    def convert_empty_strings_to_none(cls, v):
        """Convert empty strings to None for optional fields"""
        if v == '':
            return None
        return v

    @field_validator('email', mode='before')
    @classmethod
    def convert_empty_email_to_none(cls, v):
        """Convert empty email string to None"""
        if v == '':
            return None
        return v


class TicketUpdate(BaseModel):
    """Schema for updating a ticket (admin only)"""
    status: Optional[TicketStatus] = None
    description: Optional[str] = Field(None, min_length=1)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    category_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    summary: Optional[str] = None
    translation: Optional[str] = None


class CurrentAssignmentBrief(BaseModel):
    """Brief current assignment info for list view"""
    assigned_to_user_id: UUID
    assigned_to_user_name: str
    assignment_type: str
    assigned_at: str

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    """Schema for returning ticket data"""
    id: UUID
    tenant_id: UUID
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    status: TicketStatus
    description: str
    summary: Optional[str] = None
    translation: Optional[str] = None
    current_assignment: Optional[CurrentAssignmentBrief] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CurrentAssignmentDetailed(BaseModel):
    """Detailed current assignment info for detail view"""
    id: UUID
    assigned_to_user_id: UUID
    assigned_to_user_name: str
    assigned_by_user_id: Optional[UUID] = None
    assigned_by_user_name: Optional[str] = None
    assignment_type: str
    assigned_at: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class TicketSubmissionBrief(BaseModel):
    """Brief submission info for ticket detail"""
    id: UUID
    submitted_by_user_name: Optional[str] = None
    submission_type: str
    comment: str
    attachment_url: Optional[str] = None
    requires_changes: bool
    created_at: str

    class Config:
        from_attributes = True


class TicketEscalationBrief(BaseModel):
    """Brief escalation record for ticket detail"""
    id: UUID
    escalated_from_user_name: Optional[str] = None
    escalated_to_user_name: Optional[str] = None
    escalation_level: int
    reason: Optional[str] = None
    escalated_at: str

    class Config:
        from_attributes = True


class TicketDetailOut(BaseModel):
    """Detailed ticket schema with full assignment info"""
    id: UUID
    tenant_id: UUID
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    status: TicketStatus
    description: str
    summary: Optional[str] = None
    translation: Optional[str] = None
    current_assignment: Optional[CurrentAssignmentDetailed] = None
    submissions: Optional[List[TicketSubmissionBrief]] = None
    escalations: Optional[List[TicketEscalationBrief]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketAssignmentHistoryItem(BaseModel):
    """Item in assignment history"""
    id: UUID
    assigned_to_user_id: UUID
    assigned_to_user_name: str
    assigned_by_user_id: Optional[UUID] = None
    assigned_by_user_name: Optional[str] = None
    assignment_type: str
    is_current: bool
    assigned_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class TicketPublicOut(BaseModel):
    """Public-facing ticket schema — safe to return without authentication"""
    id: UUID
    title: Optional[str] = None
    description: str
    status: TicketStatus
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class APIResponse(BaseModel):
    """Generic API response model for errors"""
    detail: str
