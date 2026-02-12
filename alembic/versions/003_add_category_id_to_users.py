"""Add category_id column to users table

Revision ID: 003_add_category_id_to_users
Revises: 002_create_categories_table
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_category_id_to_users'
down_revision = '002_create_categories_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_category_id', 'users', 'categories', ['category_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_users_category_id'), 'users', ['category_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_category_id'), table_name='users')
    op.drop_constraint('fk_users_category_id', 'users', type_='foreignkey')
    op.drop_column('users', 'category_id')
