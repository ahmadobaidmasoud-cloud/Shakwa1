from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.ticket_configuration import TicketConfigurationUpdate, TicketConfigurationOut
from app.schemas.user import APIResponse
from app.crud import ticket_configuration as crud_ticket_config

router = APIRouter()


@router.get(
    "/ticket-configuration",
    response_model=TicketConfigurationOut,
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Ticket Configuration"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Configuration not found"},
    },
)
async def get_ticket_configuration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get ticket configuration for current tenant (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    ticket_config = crud_ticket_config.get_ticket_configuration_by_tenant(db, current_user.tenant_id)
    if not ticket_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket configuration not found",
        )
    return ticket_config


@router.patch(
    "/ticket-configuration",
    response_model=TicketConfigurationOut,
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Ticket Configuration"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Configuration not found"},
    },
)
async def update_ticket_configuration(
    config_data: TicketConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update ticket configuration for current tenant (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    ticket_config = crud_ticket_config.update_ticket_configuration(
        db,
        current_user.tenant_id,
        config_data,
    )
    if not ticket_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket configuration not found",
        )
    return ticket_config
