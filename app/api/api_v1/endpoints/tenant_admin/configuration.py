from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate, ConfigurationOut
from app.schemas.user import APIResponse
from app.crud.configuration import (
    get_configuration_by_id,
    get_configurations_by_tenant,
    create_configuration,
    update_configuration,
    delete_configuration,
    count_configurations,
    get_configuration_by_key,
)

router = APIRouter()

TAGS = ["Tenant Admin - Configurations"]


@router.post("/configurations", response_model=ConfigurationOut, 
             tags=TAGS,
             status_code=status.HTTP_201_CREATED)
def create_config(
    config_data: ConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create a new configuration"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    try:
        return create_configuration(db, current_user.tenant_id, config_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/configurations", response_model=list[ConfigurationOut], tags=TAGS)
def list_configurations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """List all configurations for the current tenant"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    return get_configurations_by_tenant(db, current_user.tenant_id, skip, limit)


@router.get("/configurations-count", tags=TAGS)
def get_configurations_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get count of configurations"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    return {"count": count_configurations(db, current_user.tenant_id)}


@router.get("/configurations/{config_id}", response_model=ConfigurationOut, tags=TAGS)
def get_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a specific configuration"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    config = get_configuration_by_id(db, config_id, current_user.tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.get("/configurations/by-key/{key}", response_model=ConfigurationOut, tags=TAGS)
def get_configuration_by_key_endpoint(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a configuration by key"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    config = get_configuration_by_key(db, key, current_user.tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.patch("/configurations/{config_id}", response_model=ConfigurationOut, tags=TAGS)
def update_config(
    config_id: int,
    config_data: ConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update a configuration"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    config = update_configuration(db, config_id, current_user.tenant_id, config_data)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.delete("/configurations/{config_id}", tags=TAGS)
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete a configuration"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )
    success = delete_configuration(db, config_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}
