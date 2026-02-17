"""Add category_id, title, summary, and translation columns to tickets table

Revision ID: 007_add_columns_to_tickets
Revises: 006_add_slug_to_tenants
Create Date: 2026-02-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_columns_to_tickets'
down_revision = '006_add_slug_to_tenants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category_id column (nullable, foreign key to categories)
    op.add_column('tickets', sa.Column('category_id', sa.Integer, nullable=True))
    op.create_foreign_key('fk_tickets_category_id', 'tickets', 'categories', ['category_id'], ['id'], ondelete='SET NULL')
    
    # Add title column (varchar 300)
    op.add_column('tickets', sa.Column('title', sa.String(length=300), nullable=True))
    
    # Add summary column (text)
    op.add_column('tickets', sa.Column('summary', sa.Text, nullable=True))
    
    # Add translation column (text)
    op.add_column('tickets', sa.Column('translation', sa.Text, nullable=True))


def downgrade() -> None:
    # Remove translation column
    op.drop_column('tickets', 'translation')
    
    # Remove summary column
    op.drop_column('tickets', 'summary')
    
    # Remove title column
    op.drop_column('tickets', 'title')
    
    # Remove category_id column and foreign key
    op.drop_constraint('fk_tickets_category_id', 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'category_id')
