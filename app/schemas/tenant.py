from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional


class TenantCreate(BaseModel):
    """Tenant creation request with admin user details"""
    org_name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    admin_first_name: str = Field(..., min_length=1, max_length=100, description="Admin first name")
    admin_last_name: str = Field(..., min_length=1, max_length=100, description="Admin last name")
    admin_email: EmailStr = Field(..., description="Admin email address")

    class Config:
        json_schema_extra = {
            "example": {
                "org_name": "Acme Corporation",
                "admin_first_name": "John",
                "admin_last_name": "Doe",
                "admin_email": "john.doe@acme.com"
            }
        }


class TenantUpdate(BaseModel):
    """Tenant update request"""
    org_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "org_name": "Acme Corporation Updated",
                "is_active": True
            }
        }


class TenantOut(BaseModel):
    """Tenant response schema"""
    id: UUID
    org_name: str
    slug: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "org_name": "Acme Corporation",
                "is_active": True,
                "created_at": "2024-02-10T10:00:00",
                "updated_at": "2024-02-10T10:00:00"
            }
        }
