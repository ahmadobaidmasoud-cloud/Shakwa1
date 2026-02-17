"""Create tickets table

Revision ID: 005_create_tickets_table
Revises: 004_ticket_configurations
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_create_tickets_table'
down_revision = '004_ticket_configurations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop enum if it exists
    op.execute("DROP TYPE IF EXISTS ticketstatus CASCADE")
    
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('status', postgresql.ENUM('queued', 'assigned', 'in-progress', 'processed', 'done', 'incomplete', name='ticketstatus'), nullable=False, server_default='queued'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tickets_id'), 'tickets', ['id'], unique=False)
    op.create_index(op.f('ix_tickets_tenant_id'), 'tickets', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tickets_tenant_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_id'), table_name='tickets')
    op.drop_table('tickets')
    op.execute("DROP TYPE IF EXISTS ticketstatus")
