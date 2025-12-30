"""Add created_at to analysis_history

Revision ID: 33f076018b03
Revises: 004_add_oauth_fields
Create Date: 2025-12-30 19:17:26.342450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33f076018b03'
down_revision: Union[str, None] = '004_add_oauth_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN, so we need to check if column exists first
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('analysis_history')]
    
    if 'created_at' not in existing_columns:
        # Add created_at column to analysis_history table
        op.add_column(
            'analysis_history',
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
        )
        
        # Set default value for existing rows (use analysis_timestamp as fallback)
        conn.execute(text("""
            UPDATE analysis_history 
            SET created_at = analysis_timestamp 
            WHERE created_at IS NULL
        """))
        
        # SQLite doesn't support ALTER COLUMN to change nullable
        # We'll leave it nullable for SQLite compatibility
        # PostgreSQL will enforce NOT NULL via the model default


def downgrade() -> None:
    op.drop_column('analysis_history', 'created_at')

