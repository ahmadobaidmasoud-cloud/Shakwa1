from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Generic, TypeVar, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    super_admin = "super-admin"
    admin = "admin"
    manager = "manager"
    user = "user"


# ============= REQUEST SCHEMAS =============

class UserLoginRequest(BaseModel):
    """User login request"""
    login: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=6, description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "login": "admin@example.com",
                "password": "password123"
            }
        }


class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.user)


class TenantUserCreate(BaseModel):
    """Tenant admin user creation"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.user)
    manager_id: Optional[UUID] = None
    category_id: Optional[int] = None
    is_accepting_tickets: bool = Field(default=True, description="Whether the user is accepting tickets")
    capacity: int = Field(default=10, ge=0, description="Maximum number of tickets the user can handle")


class UserUpdate(BaseModel):
    """User update schema (for editing existing users)"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    manager_id: Optional[UUID] = None
    category_id: Optional[int] = None
    is_accepting_tickets: Optional[bool] = None
    capacity: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    old_password: str = Field(..., min_length=6, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")

    class Config:
        json_schema_extra = {
            "example": {
                "old_password": "currentpassword123",
                "new_password": "newpassword456"
            }
        }


# ============= CATEGORY SCHEMA =============

class CategoryBrief(BaseModel):
    """Brief category information"""
    id: int
    name: str

    class Config:
        from_attributes = True


# ============= RESPONSE SCHEMAS =============

class ManagerBrief(BaseModel):
    """Brief manager information for user response"""
    id: UUID
    first_name: str
    last_name: str
    username: str

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    """User response schema"""
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    is_accepting_tickets: bool
    capacity: int
    assigned_tickets_count: Optional[int] = None
    tenant_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    category_id: Optional[int] = None
    category: Optional[CategoryBrief] = None
    manager: Optional[ManagerBrief] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "admin",
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "role": "super-admin",
                "is_active": True,
                "created_at": "2024-02-10T10:00:00",
                "updated_at": "2024-02-10T10:00:00"
            }
        }

class TenantBrief(BaseModel):
    """Brief tenant information for login response"""
    id: UUID
    slug: str
    org_name: str

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    """Login response with token and user info"""
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    tenant: Optional[TenantBrief] = None

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "admin",
                    "email": "admin@example.com",
                    "first_name": "Admin",
                    "last_name": "Admin",
                    "role": "super-admin",
                    "is_active": True,
                    "created_at": "2024-02-10T10:00:00",
                    "updated_at": "2024-02-10T10:00:00"
                }
            }
        }


class Msg(BaseModel):
    """Message response"""
    message: str


# Generic API Response
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic API Response wrapper"""
    status_code: int
    message: str
    data: Optional[T] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 200,
                "message": "Success",
                "data": None
            }
        }


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: str
    exp: Optional[int] = None
