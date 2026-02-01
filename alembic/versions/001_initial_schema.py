"""Initial schema with issues, actions, audit_trail, and agent_state tables

Revision ID: 001
Revises: 
Create Date: 2026-02-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create issues table
    op.create_table(
        'issues',
        sa.Column('issue_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('merchant_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('root_cause_category', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('selected_action_type', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approval_status', sa.String(length=20), nullable=True),
        sa.Column('signal_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pattern_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('issue_id')
    )
    op.create_index('idx_merchant_status', 'issues', ['merchant_id', 'status'])
    op.create_index('idx_created_at', 'issues', ['created_at'])
    op.create_index('idx_approval_status', 'issues', ['approval_status'], postgresql_where=sa.text('requires_approval = true'))
    op.create_index(op.f('ix_issues_merchant_id'), 'issues', ['merchant_id'])
    op.create_index(op.f('ix_issues_status'), 'issues', ['status'])

    # Create actions table
    op.create_table(
        'actions',
        sa.Column('action_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('issue_id', sa.Uuid(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('rollback_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rolled_back', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.issue_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('action_id')
    )
    op.create_index('idx_issue', 'actions', ['issue_id'])
    op.create_index('idx_status_created', 'actions', ['status', 'created_at'])
    op.create_index('idx_action_type_created', 'actions', ['action_type', 'created_at'])
    op.create_index(op.f('ix_actions_status'), 'actions', ['status'])

    # Create audit_trail table
    op.create_table(
        'audit_trail',
        sa.Column('audit_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('issue_id', sa.Uuid(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reasoning', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.issue_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index('idx_issue_timestamp', 'audit_trail', ['issue_id', 'timestamp'])
    op.create_index('idx_timestamp', 'audit_trail', ['timestamp'])
    op.create_index('idx_event_type_timestamp', 'audit_trail', ['event_type', 'timestamp'])
    op.create_index(op.f('ix_audit_trail_event_type'), 'audit_trail', ['event_type'])

    # Create agent_state table
    op.create_table(
        'agent_state',
        sa.Column('state_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('issue_id', sa.Uuid(), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('state_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('checkpoint_id', sa.String(length=255), nullable=True),
        sa.Column('parent_checkpoint_id', sa.String(length=255), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('state_id'),
        sa.UniqueConstraint('issue_id')
    )
    op.create_index('idx_issue_id', 'agent_state', ['issue_id'])
    op.create_index('idx_stage', 'agent_state', ['stage'])
    op.create_index('idx_updated_at', 'agent_state', ['updated_at'])

    # Create rules to prevent updates and deletes on audit_trail
    op.execute("""
        CREATE RULE audit_trail_immutable AS ON UPDATE TO audit_trail DO INSTEAD NOTHING;
    """)
    op.execute("""
        CREATE RULE audit_trail_no_delete AS ON DELETE TO audit_trail DO INSTEAD NOTHING;
    """)


def downgrade() -> None:
    # Drop rules first
    op.execute("DROP RULE IF EXISTS audit_trail_immutable ON audit_trail;")
    op.execute("DROP RULE IF EXISTS audit_trail_no_delete ON audit_trail;")
    
    # Drop tables in reverse order
    op.drop_table('agent_state')
    op.drop_table('audit_trail')
    op.drop_table('actions')
    op.drop_table('issues')
