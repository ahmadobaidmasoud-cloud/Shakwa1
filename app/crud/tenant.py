from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate
from uuid import UUID
from typing import Optional, List
import re


def generate_slug(org_name: str) -> str:
    """Generate a URL-friendly slug from organization name"""
    # Convert to lowercase
    slug = org_name.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def get_tenant_by_id(db: Session, tenant_id: UUID) -> Optional[Tenant]:
    """Get tenant by ID"""
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def get_tenant_by_org_name(db: Session, org_name: str) -> Optional[Tenant]:
    """Get tenant by organization name"""
    return db.query(Tenant).filter(Tenant.org_name == org_name).first()


def get_tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
    """Get tenant by slug"""
    return db.query(Tenant).filter(Tenant.slug == slug).first()


def get_all_tenants(db: Session, skip: int = 0, limit: int = 100) -> List[Tenant]:
    """Get all tenants with pagination"""
    return db.query(Tenant).offset(skip).limit(limit).all()


def create_tenant(db: Session, tenant_data: TenantCreate) -> Tenant:
    """Create a new tenant"""
    slug = generate_slug(tenant_data.org_name)
    
    db_tenant = Tenant(
        org_name=tenant_data.org_name,
        slug=slug,
        is_active=True,
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


def update_tenant(db: Session, tenant_id: UUID, tenant_data: TenantUpdate) -> Optional[Tenant]:
    """Update a tenant"""
    db_tenant = get_tenant_by_id(db, tenant_id)
    if not db_tenant:
        return None
    
    update_data = tenant_data.model_dump(exclude_unset=True)
    
    # If org_name is being updated, regenerate slug
    if 'org_name' in update_data:
        update_data['slug'] = generate_slug(update_data['org_name'])
    
    for field, value in update_data.items():
        setattr(db_tenant, field, value)
    
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


def delete_tenant(db: Session, tenant_id: UUID) -> bool:
    """Delete a tenant and all associated users (cascade delete)"""
    db_tenant = get_tenant_by_id(db, tenant_id)
    if not db_tenant:
        return False
    
    # Delete all users associated with this tenant
    db.query(User).filter(User.tenant_id == tenant_id).delete()
    
    # Delete the tenant
    db.delete(db_tenant)
    db.commit()
    return True


def count_tenants(db: Session) -> int:
    """Get total number of tenants"""
    return db.query(Tenant).count()
