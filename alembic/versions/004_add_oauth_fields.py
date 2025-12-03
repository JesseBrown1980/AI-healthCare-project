"""Add OAuth support to users table

Revision ID: 004_add_oauth_fields
Revises: 003_add_user_tokens
Create Date: 2025-01-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_oauth_fields'
down_revision: Union[str, None] = '003_add_user_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns already exist (for partial migrations)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add OAuth provider fields to users table (only if they don't exist)
    if 'oauth_provider' not in existing_columns:
        op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    if 'oauth_provider_id' not in existing_columns:
        op.add_column('users', sa.Column('oauth_provider_id', sa.String(255), nullable=True))
    if 'oauth_access_token' not in existing_columns:
        op.add_column('users', sa.Column('oauth_access_token', sa.Text(), nullable=True))
    if 'oauth_refresh_token' not in existing_columns:
        op.add_column('users', sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
    if 'oauth_token_expires' not in existing_columns:
        op.add_column('users', sa.Column('oauth_token_expires', sa.DateTime(timezone=True), nullable=True))
    
    # Add indexes for OAuth fields (only if they don't exist)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_oauth_provider' not in existing_indexes:
        op.create_index(op.f('ix_users_oauth_provider'), 'users', ['oauth_provider'], unique=False)
    if 'ix_users_oauth_provider_id' not in existing_indexes:
        op.create_index(op.f('ix_users_oauth_provider_id'), 'users', ['oauth_provider_id'], unique=False)
    
    # Make password_hash nullable (OAuth users don't have passwords)
    # Check current nullable status first
    password_hash_col = next((col for col in inspector.get_columns('users') if col['name'] == 'password_hash'), None)
    if password_hash_col and password_hash_col['nullable'] is False:
        op.alter_column('users', 'password_hash', nullable=True)


def downgrade() -> None:
    # Remove indexes
    op.drop_index(op.f('ix_users_oauth_provider_id'), table_name='users')
    op.drop_index(op.f('ix_users_oauth_provider'), table_name='users')
    
    # Remove OAuth columns
    op.drop_column('users', 'oauth_token_expires')
    op.drop_column('users', 'oauth_refresh_token')
    op.drop_column('users', 'oauth_access_token')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'oauth_provider')
    
    # Make password_hash required again (if needed)
    op.alter_column('users', 'password_hash', nullable=False)

