"""Add manager role to userrole enum

Revision ID: 001_add_manager_role
Revises: 
Create Date: 2026-02-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_manager_role'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'manager' value to the userrole enum type
    op.execute("ALTER TYPE userrole ADD VALUE 'manager' BEFORE 'user'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This is a limitation of PostgreSQL's ENUM type
    # You would need to create a new enum type and migrate data
    # For this example, we'll just pass
    pass
