from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryOut
from app.schemas.user import APIResponse
from app.crud import category as crud_category

router = APIRouter()


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        400: {"model": APIResponse, "description": "Validation error"},
    },
)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create a new category (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    try:
        category = crud_category.create_category(
            db,
            current_user.tenant_id,
            current_user.id,
            category_data,
        )
        return category
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/categories",
    response_model=List[CategoryOut],
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
    },
)
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """List all categories for current tenant (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    categories = crud_category.get_categories_by_tenant(
        db,
        current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return categories


@router.get(
    "/categories/{category_id}",
    response_model=CategoryOut,
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Category not found"},
    },
)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a specific category by ID (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    category = crud_category.get_category_by_id(db, category_id, current_user.tenant_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryOut,
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Category not found"},
    },
)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update a category (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    category = crud_category.update_category(
        db,
        category_id,
        current_user.tenant_id,
        category_data,
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
        404: {"model": APIResponse, "description": "Category not found"},
    },
)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete a category (Tenant Admin only)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    success = crud_category.delete_category(db, category_id, current_user.tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return None


@router.get(
    "/categories-count",
    status_code=status.HTTP_200_OK,
    tags=["Tenant Admin - Categories"],
    responses={
        403: {"model": APIResponse, "description": "Not authorized for admin"},
    },
)
async def count_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get total number of categories for current tenant"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context missing for current user",
        )

    count = crud_category.count_categories(db, current_user.tenant_id)
    return {"count": count}
