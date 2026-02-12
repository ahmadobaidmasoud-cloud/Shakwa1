from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.user import TenantUserCreate, UserOut, APIResponse
from app.crud import user as crud_user
from app.crud import tenant as crud_tenant
from app.core.email import email_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin - Users"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        400: {"model": APIResponse, "description": "Validation error"},
    },
)
async def create_tenant_user(
    user_data: TenantUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Create a user within the current tenant (Admin only).
    
    This endpoint creates a new user (manager or employee) and sends
    a welcome email with login credentials.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    try:
        # Create the user
        new_user = crud_user.create_user_in_tenant(db, current_user.tenant_id, user_data)
        
        # Get tenant info for email
        tenant = crud_tenant.get_tenant_by_id(db, current_user.tenant_id)
        if not tenant:
            logger.error(f"Tenant not found for ID: {current_user.tenant_id}")
            return new_user
        
        # Send welcome email with credentials
        email_sent = email_service.send_welcome_email(
            to_email=new_user.email,
            tenant_name=tenant.org_name,
            first_name=new_user.first_name,
            temporary_password=user_data.password,
        )
        
        if not email_sent:
            logger.warning(f"Failed to send welcome email to {new_user.email}, but user was created")
        
        return new_user
        
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/users",
    response_model=List[UserOut],
    status_code=status.HTTP_200_OK,
    tags=["Admin - Users"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
    },
)
async def list_tenant_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """List users for the current tenant (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    return crud_user.get_users_by_tenant(db, current_user.tenant_id, skip=skip, limit=limit)
