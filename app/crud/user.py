from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserLoginRequest, UserRegisterRequest, TenantUserCreate
from app.core.security import get_password_hash, verify_password
from uuid import UUID
from typing import Optional, List
import secrets
import string


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_id_in_tenant(db: Session, user_id: UUID, tenant_id: UUID) -> Optional[User]:
    """Get user by ID within a tenant"""
    return db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()


def get_user_by_login(db: Session, login: str) -> Optional[User]:
    """Get user by username or email"""
    return db.query(User).filter(
        (User.username == login) | (User.email == login)
    ).first()


def get_users_by_tenant(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[User]:
    """Get users by tenant"""
    return (
        db.query(User)
        .filter(User.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_users_by_role_in_tenant(db: Session, tenant_id: UUID, role: UserRole) -> int:
    """Count users of a specific role within a tenant"""
    return (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.role == role)
        .count()
    )


def create_user(db: Session, user_data: UserRegisterRequest) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_in_tenant(db: Session, tenant_id: UUID, user_data: TenantUserCreate) -> User:
    """Create a new user within a tenant with optional manager assignment"""
    # Enforce unique identifiers
    if get_user_by_email(db, user_data.email):
        raise ValueError("Email already registered")
    if get_user_by_username(db, user_data.username):
        raise ValueError("Username already taken")

    role_value = user_data.role.value if hasattr(user_data.role, "value") else str(user_data.role)
    if role_value not in ["manager", "user"]:
        raise ValueError("Role must be manager or user")

    # Validate manager if provided
    if user_data.manager_id:
        manager = get_user_by_id_in_tenant(db, user_data.manager_id, tenant_id)
        if not manager:
            raise ValueError("Manager not found in this tenant")

        manager_role = manager.role.value if hasattr(manager.role, "value") else str(manager.role)
        if manager_role not in ["admin", "manager"]:
            raise ValueError("Manager must have role admin or manager")

        # ── Category uniqueness for sub-managers ────────────────────
        # Each manager can only have ONE sub-manager per category
        if role_value == "manager" and user_data.category_id:
            existing_sub = db.query(User).filter(
                User.manager_id == user_data.manager_id,
                User.tenant_id == tenant_id,
                User.role == UserRole.manager,
                User.category_id == user_data.category_id,
            ).first()
            if existing_sub:
                raise ValueError(
                    f"This manager already has a sub-manager for the selected category. "
                    f"Each manager can only have one sub-manager per category."
                )

        # ── Employees must share their manager's category ───────────
        if role_value == "user" and user_data.category_id:
            mgr_category = manager.category_id
            if mgr_category and mgr_category != user_data.category_id:
                raise ValueError(
                    "Employee must belong to the same category as their manager"
                )

    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        role=user_data.role,
        tenant_id=tenant_id,
        manager_id=user_data.manager_id,
        category_id=user_data.category_id,
        is_active=True,
        is_accepting_tickets=user_data.is_accepting_tickets,
        capacity=user_data.capacity,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, login: str, password: str) -> Optional[User]:
    """Authenticate user by username/email and password"""
    user = get_user_by_login(db, login)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def update_user(db: Session, user_id: UUID, user_data: dict) -> Optional[User]:
    """Update user"""
    user = get_user_by_id(db, user_id)
    if user:
        for key, value in user_data.items():
            if value is not None:
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user


def create_tenant_admin(
    db: Session,
    email: str,
    first_name: str,
    last_name: str,
    tenant_id: UUID,
) -> tuple[User, str]:
    """
    Create a tenant admin user with a temporary password
    
    Args:
        db: Database session
        email: Admin email
        first_name: Admin first name
        last_name: Admin last name
        tenant_id: Tenant UUID to associate with the user
        
    Returns:
        Tuple of (User, temporary_password)
    """
    # Generate temporary password
    temp_password = generate_temp_password()
    hashed_password = get_password_hash(temp_password)
    
    # Generate username from email
    username = email.split('@')[0]
    # Ensure username is unique
    counter = 1
    original_username = username
    while get_user_by_username(db, username):
        username = f"{original_username}{counter}"
        counter += 1
    
    # Create user
    db_user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hashed_password,
        role=UserRole.admin,
        tenant_id=tenant_id,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user, temp_password


def generate_temp_password(length: int = 12) -> str:
    """
    Generate a temporary password with mix of uppercase, lowercase, digits, and symbols
    
    Args:
        length: Length of password to generate
        
    Returns:
        Temporary password string
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation.replace("'", "").replace('"', "")
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password


def change_password(db: Session, user_id: UUID, old_password: str, new_password: str) -> bool:
    """
    Change password for a user after verifying old password
    
    Args:
        db: Database session
        user_id: User ID
        old_password: Current password (plain text)
        new_password: New password (plain text)
        
    Returns:
        True if password changed successfully, False otherwise
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    # Verify old password
    if not verify_password(old_password, user.hashed_password):
        return False
    
    # Hash and update new password
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return True
