from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserBrief(BaseModel):
    """Brief user information"""
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class TicketAssignmentOut(BaseModel):
    """Schema for returning ticket assignment data"""
    id: UUID
    ticket_id: UUID
    assigned_to_user_id: UUID
    assigned_by_user_id: Optional[UUID] = None
    assignment_type: str
    is_current: bool
    assigned_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketAssignmentWithUser(BaseModel):
    """Schema for returning ticket assignment with user details"""
    id: UUID
    ticket_id: UUID
    assigned_to_user: UserBrief
    assigned_by_user: Optional[UserBrief] = None
    assignment_type: str
    is_current: bool
    assigned_at: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketAssignmentCreate(BaseModel):
    """Schema for creating ticket assignment"""
    ticket_id: UUID
    assigned_to_user_id: UUID
    assigned_by_user_id: Optional[UUID] = None
    assignment_type: str = Field(default="assigned", min_length=1)
    notes: Optional[str] = None


class TicketAssignmentUpdate(BaseModel):
    """Schema for updating ticket assignment"""
    is_current: Optional[bool] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class AssignTicketRequest(BaseModel):
    """Schema for assigning a ticket to a user"""
    assigned_to_user_id: UUID = Field(..., description="User ID to assign ticket to")
    notes: Optional[str] = Field(None, description="Assignment notes")


class TicketEscalationOut(BaseModel):
    """Schema for returning ticket escalation data"""
    id: UUID
    ticket_id: UUID
    escalated_from_user_id: UUID
    escalated_to_user_id: UUID
    escalation_level: int
    reason: Optional[str] = None
    escalated_at: str
    created_at: str

    class Config:
        from_attributes = True


class TicketEscalationCreate(BaseModel):
    """Schema for creating ticket escalation"""
    ticket_id: UUID
    escalated_from_user_id: UUID
    escalated_to_user_id: UUID
    escalation_level: int
    reason: Optional[str] = None
