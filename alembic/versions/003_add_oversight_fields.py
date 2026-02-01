"""Add oversight and reasoning fields to actions and issues

Revision ID: 003
Revises: 002
Create Date: 2026-02-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reasoning field to actions table
    op.add_column('actions', sa.Column('reasoning', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add resolution tracking fields to issues table
    op.add_column('issues', sa.Column('resolution_type', sa.String(length=50), nullable=True))
    op.add_column('issues', sa.Column('root_cause_reasoning', sa.String(length=1000), nullable=True))
    op.add_column('issues', sa.Column('reasoning_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove fields from issues table
    op.drop_column('issues', 'reasoning_chain')
    op.drop_column('issues', 'root_cause_reasoning')
    op.drop_column('issues', 'resolution_type')
    
    # Remove field from actions table
    op.drop_column('actions', 'reasoning')
