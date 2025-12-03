"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-26 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('patient_id', sa.String(255), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('fhir_resource_id', sa.String(255), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_hash')
    )
    op.create_index(op.f('ix_documents_patient_id'), 'documents', ['patient_id'], unique=False)

    # Create analysis_history table
    op.create_table(
        'analysis_history',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('patient_id', sa.String(255), nullable=False),
        sa.Column('analysis_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analysis_data', sa.JSON(), nullable=True),
        sa.Column('risk_scores', sa.JSON(), nullable=True),
        sa.Column('alerts', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('correlation_id', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_history_patient_id'), 'analysis_history', ['patient_id'], unique=False)
    op.create_index(op.f('ix_analysis_history_analysis_timestamp'), 'analysis_history', ['analysis_timestamp'], unique=False)
    op.create_index(op.f('ix_analysis_history_user_id'), 'analysis_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_analysis_history_correlation_id'), 'analysis_history', ['correlation_id'], unique=False)

    # Create ocr_extractions table
    op.create_table(
        'ocr_extractions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('extraction_type', sa.String(50), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('normalized_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_extractions_document_id'), 'ocr_extractions', ['document_id'], unique=False)

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_last_activity'), 'user_sessions', ['last_activity'], unique=False)

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('correlation_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('patient_id', sa.String(255), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('outcome', sa.String(10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_correlation_id'), 'audit_logs', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_patient_id'), 'audit_logs', ['patient_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_patient_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_correlation_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_user_sessions_last_activity'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_expires_at'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_ocr_extractions_document_id'), table_name='ocr_extractions')
    op.drop_table('ocr_extractions')
    op.drop_index(op.f('ix_analysis_history_correlation_id'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_user_id'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_analysis_timestamp'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_patient_id'), table_name='analysis_history')
    op.drop_table('analysis_history')
    op.drop_index(op.f('ix_documents_patient_id'), table_name='documents')
    op.drop_table('documents')

