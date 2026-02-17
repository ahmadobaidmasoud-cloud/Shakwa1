from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import logging

from app.db.session import get_db
from app.schemas.ticket import TicketCreate, TicketOut, APIResponse
from app.schemas.ticket_configuration import TicketConfigurationOut
from app.crud import ticket as crud_ticket
from app.crud import ticket_configuration as crud_ticket_config
from app.crud import tenant as crud_tenant
from app.models.tenant import Tenant
from app.core.speechmatics import generate_speechmatics_token
from app.core.ticket_process import process_ticket_in_background

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Public - Tickets"],
    responses={
        400: {"model": APIResponse, "description": "Validation error"},
        404: {"model": APIResponse, "description": "Tenant not found"},
    },
)
async def create_ticket_public(
    ticket_data: TicketCreate = Body(...),
    tenant_id: Optional[UUID] = Query(None),
    tenant_slug: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """
    Create a new ticket publicly (no authentication required).
    
    Either tenant_id (UUID) or tenant_slug (string) is required.
    
    After creation, tickets are enriched in the background with:
    - AI-generated title
    - AI-generated summary
    - Translated description
    """
    # Get tenant based on provided parameter
    tenant = None
    if tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    elif tenant_slug:
        tenant = crud_tenant.get_tenant_by_slug(db, tenant_slug)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either tenant_id or tenant_slug is required",
        )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is not active",
        )

    try:
        ticket = crud_ticket.create_ticket(db, tenant.id, ticket_data)
        
        # Trigger background processing to enrich ticket
        background_tasks.add_task(
            process_ticket_in_background, 
            db=db, 
            ticket_id=ticket.id, 
            tenant_id=tenant.id
        )
        
        logger.info(f"Ticket {ticket.id} created, background processing queued")
        return ticket
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/tickets/config",
    response_model=TicketConfigurationOut,
    status_code=status.HTTP_200_OK,
    tags=["Public - Tickets"],
    responses={
        404: {"model": APIResponse, "description": "Tenant or configuration not found"},
    },
)
async def get_ticket_config_public(
    tenant_slug: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get ticket configuration for a tenant by slug (public, no authentication required).
    """
    # Get tenant by slug
    tenant = crud_tenant.get_tenant_by_slug(db, tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is not active",
        )

    # Get ticket configuration for tenant
    config = crud_ticket_config.get_ticket_configuration_by_tenant(db, tenant.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket configuration not found for this tenant",
        )

    return config


@router.get(
    "/speechmatics/jwt",
    status_code=status.HTTP_200_OK,
    tags=["Public - Speechmatics"],
    responses={
        500: {"description": "Failed to generate token"},
    },
)
async def get_speechmatics_jwt():
    """
    Get a temporary token for Speechmatics real-time speech-to-text API.
    Calls Speechmatics API to generate a time-limited token (default: 60 seconds).
    No authentication required (public endpoint).
    """
    try:
        result = await generate_speechmatics_token(ttl=60)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(exc)}",
        )

