from sqlalchemy.orm import Session
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from uuid import UUID
from typing import Optional, List


def get_category_by_id(db: Session, category_id: int, tenant_id: UUID) -> Optional[Category]:
    """Get category by ID for a specific tenant"""
    return db.query(Category).filter(
        Category.id == category_id,
        Category.tenant_id == tenant_id
    ).first()


def get_categories_by_tenant(
    db: Session,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> List[Category]:
    """Get all categories for a tenant"""
    return db.query(Category).filter(
        Category.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()


def create_category(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_data: CategoryCreate,
) -> Category:
    """Create a new category"""
    db_category = Category(
        tenant_id=tenant_id,
        user_id=user_id,
        name=category_data.name.strip(),
        description=category_data.description,
        keywords=category_data.keywords,
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(
    db: Session,
    category_id: int,
    tenant_id: UUID,
    category_data: CategoryUpdate,
) -> Optional[Category]:
    """Update a category"""
    db_category = get_category_by_id(db, category_id, tenant_id)
    if not db_category:
        return None
    
    update_data = category_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_category, field, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category


def delete_category(db: Session, category_id: int, tenant_id: UUID) -> bool:
    """Delete a category"""
    db_category = get_category_by_id(db, category_id, tenant_id)
    if not db_category:
        return False
    
    db.delete(db_category)
    db.commit()
    return True


def count_categories(db: Session, tenant_id: UUID) -> int:
    """Count total categories for a tenant"""
    return db.query(Category).filter(Category.tenant_id == tenant_id).count()
