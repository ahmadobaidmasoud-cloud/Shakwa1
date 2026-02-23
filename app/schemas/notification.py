from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    ticket_assigned = "ticket_assigned"
    ticket_completed = "ticket_completed"
    ticket_rejected = "ticket_rejected"
    ticket_approved = "ticket_approved"
    manager_message = "manager_message"
    system = "system"


class NotificationCreate(BaseModel):
    """Create notification request"""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    notification_type: NotificationType
    user_id: UUID
    ticket_id: Optional[UUID] = None
    related_user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    """Notification response schema"""
    id: UUID
    user_id: UUID
    title: str
    message: str
    notification_type: NotificationType
    is_read: bool
    ticket_id: Optional[UUID] = None
    related_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    """Update notification request"""
    is_read: Optional[bool] = None

    class Config:
        from_attributes = True
