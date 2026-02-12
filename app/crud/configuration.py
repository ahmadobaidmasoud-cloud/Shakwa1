from sqlalchemy.orm import Session
from app.models.configuration import Configuration
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate
from uuid import UUID
from typing import Optional, List
import re


def generate_key_from_label(label: str) -> str:
    """Generate key from label: convert to lowercase and replace spaces with underscores"""
    key = label.lower()
    key = re.sub(r'\s+', '_', key)  # Replace spaces with underscores
    key = re.sub(r'[^a-z0-9_]', '', key)  # Remove special characters
    return key


def get_configuration_by_id(db: Session, config_id: int, tenant_id: UUID) -> Optional[Configuration]:
    """Get configuration by ID and tenant"""
    return db.query(Configuration).filter(
        Configuration.id == config_id,
        Configuration.tenant_id == tenant_id
    ).first()


def get_configuration_by_key(db: Session, key: str, tenant_id: UUID) -> Optional[Configuration]:
    """Get configuration by key and tenant"""
    return db.query(Configuration).filter(
        Configuration.key == key,
        Configuration.tenant_id == tenant_id
    ).first()


def get_configurations_by_tenant(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Configuration]:
    """Get all configurations for a tenant"""
    return db.query(Configuration).filter(
        Configuration.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()


def create_configuration(
    db: Session,
    tenant_id: UUID,
    config_data: ConfigurationCreate,
) -> Configuration:
    """Create a new configuration"""
    # Generate key if not provided
    key = config_data.key if config_data.key else generate_key_from_label(config_data.label)
    
    # Check if key already exists for this tenant
    existing = get_configuration_by_key(db, key, tenant_id)
    if existing:
        raise ValueError(f"Configuration key '{key}' already exists for this tenant")

    config = Configuration(
        tenant_id=tenant_id,
        label=config_data.label,
        key=key,
        value_type=config_data.value_type,
        value=config_data.value,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_configuration(
    db: Session,
    config_id: int,
    tenant_id: UUID,
    config_data: ConfigurationUpdate,
) -> Optional[Configuration]:
    """Update a configuration"""
    config = get_configuration_by_id(db, config_id, tenant_id)
    if not config:
        return None

    # Update only provided fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "label" and value:
            setattr(config, field, value)
            # Auto-update key if label changed
            setattr(config, "key", generate_key_from_label(value))
        else:
            setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config


def delete_configuration(db: Session, config_id: int, tenant_id: UUID) -> bool:
    """Delete a configuration"""
    config = get_configuration_by_id(db, config_id, tenant_id)
    if not config:
        return False

    db.delete(config)
    db.commit()
    return True


def count_configurations(db: Session, tenant_id: UUID) -> int:
    """Get count of configurations for a tenant"""
    return db.query(Configuration).filter(Configuration.tenant_id == tenant_id).count()


def create_default_configuration(db: Session, tenant_id: UUID) -> Configuration:
    """Create a default configuration for a tenant when it's created"""
    for config in [
        {"label": "SLA", "value_type": "int", "value": "60"}]:
        create_configuration(db, tenant_id, ConfigurationCreate(**config))
    return get_configurations_by_tenant(db, tenant_id)