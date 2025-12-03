"""Add Consent and TwoFactorAuth models

Revision ID: 9a872a660cf0
Revises: 33f076018b03
Create Date: 2026-01-03 18:56:37.275179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '9a872a660cf0'
down_revision: Union[str, None] = '33f076018b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create consents table
    op.create_table('consents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('accepted', sa.Integer(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('consent_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_consent_user_accepted', 'consents', ['user_id', 'accepted'], unique=False)
    op.create_index('idx_consent_user_type', 'consents', ['user_id', 'consent_type'], unique=False)
    op.create_index(op.f('ix_consents_created_at'), 'consents', ['created_at'], unique=False)
    op.create_index(op.f('ix_consents_user_id'), 'consents', ['user_id'], unique=False)
    
    # Create two_factor_auth table
    op.create_table('two_factor_auth',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('secret_key', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=True),
        sa.Column('backup_codes', sa.JSON(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_2fa_user_enabled', 'two_factor_auth', ['user_id', 'enabled'], unique=False)
    op.create_index(op.f('ix_two_factor_auth_created_at'), 'two_factor_auth', ['created_at'], unique=False)
    op.create_index(op.f('ix_two_factor_auth_user_id'), 'two_factor_auth', ['user_id'], unique=True)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_two_factor_auth_user_id'), table_name='two_factor_auth')
    op.drop_index(op.f('ix_two_factor_auth_created_at'), table_name='two_factor_auth')
    op.drop_index('idx_2fa_user_enabled', table_name='two_factor_auth')
    op.drop_index(op.f('ix_consents_user_id'), table_name='consents')
    op.drop_index(op.f('ix_consents_created_at'), table_name='consents')
    op.drop_index('idx_consent_user_type', table_name='consents')
    op.drop_index('idx_consent_user_accepted', table_name='consents')
    
    # Drop tables
    op.drop_table('two_factor_auth')
    op.drop_table('consents')
