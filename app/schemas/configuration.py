from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class ConfigurationCreate(BaseModel):
    """Create configuration request"""
    label: str = Field(..., min_length=1, max_length=100, description="User-friendly label")
    key: Optional[str] = Field(None, max_length=100, description="Auto-generated key from label if not provided")
    value_type: str = Field(..., description="Type of value: string, int, boolean, json")
    value: Optional[str] = Field(None, description="Configuration value as string")

    class Config:
        json_schema_extra = {
            "example": {
                "label": "Max Attachments",
                "key": "max_attachments",
                "value_type": "int",
                "value": "5"
            }
        }


class ConfigurationUpdate(BaseModel):
    """Update configuration request"""
    label: Optional[str] = Field(None, max_length=100)
    value_type: Optional[str] = None
    value: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "label": "Max Attachments",
                "value_type": "int",
                "value": "10"
            }
        }


class ConfigurationOut(BaseModel):
    """Configuration response schema"""
    id: int
    tenant_id: UUID
    label: str
    key: str
    value_type: str
    value: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "label": "Max Attachments",
                "key": "max_attachments",
                "value_type": "int",
                "value": "5",
                "created_at": "2024-02-10T10:00:00",
                "updated_at": "2024-02-10T10:00:00"
            }
        }
