"""
Database seeding script - Creates initial super-admin user for testing
Run this once after your database is set up:
    python seed_db.py
"""

from app.db.session import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy.exc import IntegrityError


def seed_database():
    """Create initial tables and seed with test data"""
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully\n")
    
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("⚠ Admin user already exists, skipping...\n")
            return
        
        # Create super-admin user
        super_admin = User(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.super_admin,
            is_active=True
        )
        
        db.add(super_admin)
        db.commit()
        
        print("✓ Super-admin user created successfully\n")
        print("Test Credentials:")
        print("  Username: admin")
        print("  Email: admin@example.com")
        print("  Password: password123")
        print("  Role: super-admin")
        print()
        
    except IntegrityError:
        db.rollback()
        print("⚠ User already exists\n")
    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding database: {str(e)}\n")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
