from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryCreate(BaseModel):
    """Category creation request"""
    name: str = Field(..., min_length=1, max_length=30, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    keywords: Optional[str] = Field(None, max_length=300, description="Keywords")


class CategoryUpdate(BaseModel):
    """Category update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=30)
    description: Optional[str] = Field(None)
    keywords: Optional[str] = Field(None, max_length=300)


class CategoryOut(BaseModel):
    """Category response schema"""
    id: int
    name: str
    description: Optional[str]
    keywords: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
