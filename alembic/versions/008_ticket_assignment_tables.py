"""Create ticket_assignments and ticket_escalations tables

Revision ID: 008_ticket_assignment_tables
Revises: 007_add_columns_to_tickets
Create Date: 2026-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_ticket_assignment_tables'
down_revision = '007_add_columns_to_tickets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ticket_assignments table
    op.create_table(
        'ticket_assignments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_to_user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by_user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assignment_type', sa.String(50), nullable=False, server_default='assigned'),  # assigned, escalated, reassigned
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_at', sa.String, nullable=False),
        sa.Column('completed_at', sa.String, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.String, nullable=False),
        sa.Column('updated_at', sa.String, nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name='fk_assignments_ticket_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], name='fk_assignments_assigned_to', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], name='fk_assignments_assigned_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ticket_assignments_ticket_id', 'ticket_id'),
        sa.Index('idx_ticket_assignments_assigned_to', 'assigned_to_user_id'),
        sa.Index('idx_ticket_assignments_is_current', 'is_current'),
    )

    # Create ticket_escalations table (for detailed escalation tracking)
    op.create_table(
        'ticket_escalations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('escalated_from_user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('escalated_to_user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('escalation_level', sa.Integer(), nullable=False),  # 0=employee, 1=manager, 2=senior manager, etc
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('escalated_at', sa.String, nullable=False),
        sa.Column('created_at', sa.String, nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name='fk_escalations_ticket_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['escalated_from_user_id'], ['users.id'], name='fk_escalations_from_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['escalated_to_user_id'], ['users.id'], name='fk_escalations_to_user', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_ticket_escalations_ticket_id', 'ticket_id'),
        sa.Index('idx_ticket_escalations_from_user', 'escalated_from_user_id'),
        sa.Index('idx_ticket_escalations_to_user', 'escalated_to_user_id'),
    )


def downgrade() -> None:
    op.drop_table('ticket_escalations')
    op.drop_table('ticket_assignments')
