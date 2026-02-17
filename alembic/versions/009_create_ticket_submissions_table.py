"""Add ticket_submissions table for storing employee submissions and manager reviews

Revision ID: 009_create_ticket_submissions_table
Revises: 008_ticket_assignment_tables
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_create_ticket_submissions_table'
down_revision = '008_ticket_assignment_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the ticket_submissions table
    op.create_table(
        'ticket_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submitted_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submission_type', sa.String(50), nullable=False, server_default='employee_submission'),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('requires_changes', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_submissions_created_at'), 'ticket_submissions', ['created_at'], unique=False)
    op.create_index(op.f('ix_ticket_submissions_submitted_by_user_id'), 'ticket_submissions', ['submitted_by_user_id'], unique=False)
    op.create_index(op.f('ix_ticket_submissions_ticket_id'), 'ticket_submissions', ['ticket_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ticket_submissions_submitted_by_user_id'), table_name='ticket_submissions')
    op.drop_index(op.f('ix_ticket_submissions_ticket_id'), table_name='ticket_submissions')
    op.drop_index(op.f('ix_ticket_submissions_created_at'), table_name='ticket_submissions')
    op.drop_table('ticket_submissions')
