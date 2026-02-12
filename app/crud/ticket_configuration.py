from sqlalchemy.orm import Session
from app.models.ticket_configuration import TicketConfiguration
from app.schemas.ticket_configuration import TicketConfigurationUpdate
from uuid import UUID
from typing import Optional


def get_ticket_configuration_by_tenant(db: Session, tenant_id: UUID) -> Optional[TicketConfiguration]:
    """Get ticket configuration for a tenant"""
    return db.query(TicketConfiguration).filter(TicketConfiguration.tenant_id == tenant_id).first()


def create_ticket_configuration(db: Session, tenant_id: UUID) -> TicketConfiguration:
    """
    Create a default ticket configuration for a tenant.
    Called when a tenant is created.
    """
    ticket_config = TicketConfiguration(
        tenant_id=tenant_id,
        first_name=True,
        last_name=True,
        email=True,
        phone=False,
        details=True,
    )
    db.add(ticket_config)
    db.commit()
    db.refresh(ticket_config)
    return ticket_config


def update_ticket_configuration(
    db: Session,
    tenant_id: UUID,
    config_data: TicketConfigurationUpdate,
) -> Optional[TicketConfiguration]:
    """Update ticket configuration for a tenant"""
    ticket_config = get_ticket_configuration_by_tenant(db, tenant_id)
    if not ticket_config:
        return None

    # Update only provided fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket_config, field, value)

    db.commit()
    db.refresh(ticket_config)
    return ticket_config
