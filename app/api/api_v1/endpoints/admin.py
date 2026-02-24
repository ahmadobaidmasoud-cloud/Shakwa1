from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.user import TenantUserCreate, UserOut, UserUpdate, APIResponse
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

    from app.models.ticket import Ticket
    from app.models.ticket_assignment import TicketAssignment
    from app.schemas.user import UserOut as UserOutSchema

    users = crud_user.get_users_by_tenant(db, current_user.tenant_id, skip=skip, limit=limit)

    # Enrich each user with their current active ticket count
    enriched = []
    for user in users:
        count = (
            db.query(TicketAssignment)
            .join(Ticket, TicketAssignment.ticket_id == Ticket.id)
            .filter(
                TicketAssignment.assigned_to_user_id == user.id,
                TicketAssignment.is_current == True,
                Ticket.status.notin_(["processed", "done", "incomplete"]),
            )
            .count()
        )
        out = UserOutSchema.model_validate(user)
        out.assigned_tickets_count = count
        enriched.append(out)

    return enriched


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    tags=["Admin - Users"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "User not found"},
    },
)
async def get_tenant_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a specific user from the current tenant (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    user = crud_user.get_user_by_id_in_tenant(db, user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    tags=["Admin - Users"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "User not found"},
        400: {"model": APIResponse, "description": "Validation error"},
    },
)
async def update_tenant_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update a user within the current tenant (Admin only)."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    # Verify user exists in tenant
    user = crud_user.get_user_by_id_in_tenant(db, user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        # Validate manager if provided
        if user_data.manager_id:
            manager = crud_user.get_user_by_id_in_tenant(db, user_data.manager_id, current_user.tenant_id)
            if not manager:
                raise ValueError("Manager not found in this tenant")

            manager_role = manager.role.value if hasattr(manager.role, "value") else str(manager.role)
            if manager_role not in ["admin", "manager"]:
                raise ValueError("Manager must have role admin or manager")

        # Build update payload with only provided fields
        update_payload = {}
        if user_data.first_name is not None:
            update_payload['first_name'] = user_data.first_name
        if user_data.last_name is not None:
            update_payload['last_name'] = user_data.last_name
        if user_data.role is not None:
            update_payload['role'] = user_data.role
        if user_data.manager_id is not None:
            update_payload['manager_id'] = user_data.manager_id
        if user_data.category_id is not None:
            update_payload['category_id'] = user_data.category_id
        if user_data.is_accepting_tickets is not None:
            update_payload['is_accepting_tickets'] = user_data.is_accepting_tickets
        if user_data.capacity is not None:
            update_payload['capacity'] = user_data.capacity

        # Update user
        updated_user = crud_user.update_user(db, user_id, update_payload)
        return updated_user

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
