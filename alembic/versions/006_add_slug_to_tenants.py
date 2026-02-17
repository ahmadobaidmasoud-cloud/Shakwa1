"""Add slug column to tenants table

Revision ID: 006_add_slug_to_tenants
Revises: 005_create_tickets_table
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import re

# revision identifiers, used by Alembic.
revision = '006_add_slug_to_tenants'
down_revision = '005_create_tickets_table'
branch_labels = None
depends_on = None


def generate_slug(org_name: str) -> str:
    """Generate a URL-friendly slug from organization name"""
    slug = org_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    return slug


def upgrade() -> None:
    # Add slug column (nullable first for existing records)
    op.add_column('tenants', sa.Column('slug', sa.String(length=255), nullable=True))
    
    # Get connection to populate existing tenants with slugs
    connection = op.get_bind()
    
    # Fetch all tenants and generate slugs
    result = connection.execute(sa.text("SELECT id, org_name FROM tenants"))
    tenants = result.fetchall()
    
    # Update each tenant with generated slug
    for tenant_id, org_name in tenants:
        slug = generate_slug(org_name)
        connection.execute(
            sa.text("UPDATE tenants SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": str(tenant_id)}
        )
    
    connection.commit()
    
    # Now make slug column non-nullable and add constraints
    op.alter_column('tenants', 'slug', nullable=False)
    op.create_unique_constraint('uq_tenants_slug', 'tenants', ['slug'])
    op.create_index(op.f('ix_tenants_slug'), 'tenants', ['slug'], unique=False)


def downgrade() -> None:
    # Drop index and constraint
    op.drop_index(op.f('ix_tenants_slug'), table_name='tenants')
    op.drop_constraint('uq_tenants_slug', 'tenants', type_='unique')
    # Drop column
    op.drop_column('tenants', 'slug')
