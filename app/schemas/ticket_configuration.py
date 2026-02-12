from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class TicketConfigurationUpdate(BaseModel):
    """Update ticket configuration fields"""
    first_name: Optional[bool] = None
    last_name: Optional[bool] = None
    email: Optional[bool] = None
    phone: Optional[bool] = None
    details: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": True,
                "last_name": True,
                "email": True,
                "phone": False,
                "details": True
            }
        }


class TicketConfigurationOut(BaseModel):
    """Ticket configuration response schema"""
    id: int
    tenant_id: UUID
    first_name: bool
    last_name: bool
    email: bool
    phone: bool
    details: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "first_name": True,
                "last_name": True,
                "email": True,
                "phone": False,
                "details": True,
                "created_at": "2024-02-10T10:00:00",
                "updated_at": "2024-02-10T10:00:00"
            }
        }
