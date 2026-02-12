from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_Super_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantOut
from app.schemas.user import APIResponse
from app.crud import tenant as crud_tenant
from app.crud import user as crud_user
from app.core.email import email_service

router = APIRouter()


# ============= TENANT CRUD ENDPOINTS =============

@router.post(
    "/tenants",
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Super Admin - Tenants"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
        400: {"model": APIResponse, "description": "Organization name or email already exists"},
    }
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    Create a new tenant with admin user (Super Admin only).
    
    This endpoint:
    1. Creates a new organization/tenant
    2. Creates an admin user for that tenant
    3. Sends welcome email with temporary password
    4. Associates the admin user with the tenant
    
    Args:
    - **org_name**: Organization name (unique)
    - **admin_first_name**: Admin user first name
    - **admin_last_name**: Admin user last name
    - **admin_email**: Admin user email (unique)
    
    Returns:
    - Tenant object with ID and metadata
    """
    # Check if tenant with same org_name already exists
    existing_tenant = crud_tenant.get_tenant_by_org_name(db, tenant_data.org_name)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with organization name '{tenant_data.org_name}' already exists"
        )
    
    # Check if email already exists
    existing_user = crud_user.get_user_by_email(db, tenant_data.admin_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{tenant_data.admin_email}' already exists"
        )
    
    # Create tenant first (just the org_name, admin creation is done separately)
    db_tenant = Tenant(
        org_name=tenant_data.org_name,
        is_active=True,
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    tenant = db_tenant
    
    try:
        # Create admin user associated with tenant
        admin_user, temp_password = crud_user.create_tenant_admin(
            db,
            email=tenant_data.admin_email,
            first_name=tenant_data.admin_first_name,
            last_name=tenant_data.admin_last_name,
            tenant_id=tenant.id,
        )

        # Now we need to create ticket_configuration for the tenant with default values
        from app.crud import ticket_configuration as crud_ticket_config
        crud_ticket_config.create_ticket_configuration(db, tenant.id)

        # create default configuration for the tenant
        from app.crud import configuration as crud_configuration
        crud_configuration.create_default_configuration(db, tenant.id)
        
        # Send welcome email
        email_sent = email_service.send_welcome_email(
            to_email=tenant_data.admin_email,
            tenant_name=tenant_data.org_name,
            first_name=tenant_data.admin_first_name,
            temporary_password=temp_password,
        )
        
        if not email_sent:
            # Log warning but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send welcome email to {tenant_data.admin_email}, but tenant and user were created")
        
        return tenant
        
    except Exception as e:
        # If user creation or email fails, delete the tenant
        crud_tenant.delete_tenant(db, tenant.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating tenant admin: {str(e)}"
        )


@router.get(
    "/tenants",
    response_model=List[TenantOut],
    status_code=status.HTTP_200_OK,
    tags=["Super Admin - Tenants"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
    }
)
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    List all tenants with pagination (Super Admin only).
    
    Args:
    - **skip**: Number of tenants to skip (default: 0)
    - **limit**: Maximum number of tenants to return (default: 100)
    
    Returns:
    - List of tenant objects
    """
    tenants = crud_tenant.get_all_tenants(db, skip=skip, limit=limit)
    return tenants


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantOut,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin - Tenants"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
        404: {"model": APIResponse, "description": "Tenant not found"},
    }
)
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    Get a specific tenant by ID (Super Admin only).
    
    Args:
    - **tenant_id**: UUID of the tenant
    
    Returns:
    - Tenant object
    """
    tenant = crud_tenant.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantOut,
    status_code=status.HTTP_200_OK,
    tags=["Super Admin - Tenants"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
        404: {"model": APIResponse, "description": "Tenant not found"},
        400: {"model": APIResponse, "description": "Organization name already exists"},
    }
)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    Update a tenant (Super Admin only).
    
    Partial updates supported - only provide fields you want to update.
    
    Args:
    - **tenant_id**: UUID of the tenant
    - **org_name**: New organization name (optional)
    - **is_active**: Activate or deactivate tenant (optional)
    
    Returns:
    - Updated tenant object
    """
    tenant = crud_tenant.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if new org_name is unique (if provided and different)
    if tenant_data.org_name and tenant_data.org_name != tenant.org_name:
        existing_tenant = crud_tenant.get_tenant_by_org_name(db, tenant_data.org_name)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with organization name '{tenant_data.org_name}' already exists"
            )
    
    updated_tenant = crud_tenant.update_tenant(db, tenant_id, tenant_data)
    return updated_tenant


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Super Admin - Tenants"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
        404: {"model": APIResponse, "description": "Tenant not found"},
    }
)
async def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    Delete a tenant (Super Admin only).
    
    WARNING: This will permanently delete the tenant and associated data.
    
    Args:
    - **tenant_id**: UUID of the tenant
    """
    tenant = crud_tenant.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    crud_tenant.delete_tenant(db, tenant_id)
    return None


# ============= STATISTICS ENDPOINTS =============

@router.get(
    "/stats/tenants-count",
    status_code=status.HTTP_200_OK,
    tags=["Super Admin - Statistics"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for super admin"},
    }
)
async def tenants_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_Super_admin)
):
    """
    Get total number of tenants (Super Admin only).
    
    Returns:
    - Count of all tenants in the system
    """
    count = crud_tenant.count_tenants(db)
    return {"count": count}
