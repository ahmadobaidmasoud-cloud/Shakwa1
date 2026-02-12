"""Create ticket_configurations table

Revision ID: 004_ticket_configurations
Revises: 003_add_category_id_to_users
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_ticket_configurations'
down_revision = '003_add_category_id_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ticket_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_name', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('phone', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('details', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index(op.f('ix_ticket_configurations_id'), 'ticket_configurations', ['id'], unique=False)
    op.create_index(op.f('ix_ticket_configurations_tenant_id'), 'ticket_configurations', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ticket_configurations_tenant_id'), table_name='ticket_configurations')
    op.drop_index(op.f('ix_ticket_configurations_id'), table_name='ticket_configurations')
    op.drop_table('ticket_configurations')
