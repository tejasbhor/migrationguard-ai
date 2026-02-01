"""Create signals hypertable with TimescaleDB

Revision ID: 002
Revises: 001
Create Date: 2026-02-01 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create signals table
    op.create_table(
        'signals',
        sa.Column('signal_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('merchant_id', sa.String(length=255), nullable=False),
        sa.Column('migration_stage', sa.String(length=100), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('affected_resource', sa.String(length=255), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('issue_id', sa.Uuid(), nullable=True),
        sa.Column('pattern_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.issue_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('signal_id', 'timestamp')  # Composite key for hypertable
    )
    
    # Create indexes
    op.create_index('idx_timestamp', 'signals', ['timestamp'], postgresql_using='btree')
    op.create_index('idx_merchant_timestamp', 'signals', ['merchant_id', 'timestamp'], postgresql_using='btree')
    op.create_index('idx_source_timestamp', 'signals', ['source', 'timestamp'], postgresql_using='btree')
    op.create_index(op.f('ix_signals_merchant_id'), 'signals', ['merchant_id'])
    op.create_index(op.f('ix_signals_source'), 'signals', ['source'])

    # Convert to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable('signals', 'timestamp', 
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)

    # Enable compression on the hypertable
    op.execute("""
        ALTER TABLE signals SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'merchant_id,source'
        );
    """)

    # Add compression policy (compress data older than 7 days)
    op.execute("""
        SELECT add_compression_policy('signals', INTERVAL '7 days', if_not_exists => TRUE);
    """)

    # Add retention policy (optional - keep data for 90 days)
    op.execute("""
        SELECT add_retention_policy('signals', INTERVAL '90 days', if_not_exists => TRUE);
    """)


def downgrade() -> None:
    # Remove TimescaleDB policies
    op.execute("""
        SELECT remove_retention_policy('signals', if_exists => TRUE);
    """)
    op.execute("""
        SELECT remove_compression_policy('signals', if_exists => TRUE);
    """)
    
    # Drop table (this will also remove the hypertable)
    op.drop_table('signals')
