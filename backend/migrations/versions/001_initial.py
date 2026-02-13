"""Initial migration - create all tables

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-15

Creates all database tables for the Assessment Ops Platform:
- students: Student records with identity fields
- tests: Assessment test configurations with marking schemes
- attempts: Individual assessment attempt events
- attempt_scores: Computed scores for attempts
- flags: Manual review flags on attempts

Also creates indexes for common query patterns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Students Table ────────────────────────────────────────
    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── Tests Table ───────────────────────────────────────────
    op.create_table(
        'tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('max_marks', sa.Integer(), nullable=False, server_default='400'),
        sa.Column('negative_marking', postgresql.JSONB(), nullable=False,
                  server_default='{"correct": 4, "wrong": -1, "skip": 0}'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── Attempts Table ────────────────────────────────────────
    op.create_table(
        'attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('students.id'), nullable=False),
        sa.Column('test_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tests.id'), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answers', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='INGESTED'),
        sa.Column('duplicate_of_attempt_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('attempts.id'), nullable=True),
    )

    # Indexes for common query patterns on attempts
    op.create_index('ix_attempts_student_id', 'attempts', ['student_id'])
    op.create_index('ix_attempts_test_id', 'attempts', ['test_id'])
    op.create_index('ix_attempts_status', 'attempts', ['status'])
    op.create_index('ix_attempts_started_at', 'attempts', ['started_at'])
    op.create_index('ix_attempts_source_event_id', 'attempts', ['source_event_id'])

    # ── Attempt Scores Table ──────────────────────────────────
    op.create_table(
        'attempt_scores',
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('attempts.id'), primary_key=True),
        sa.Column('correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wrong', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accuracy', sa.Numeric(precision=10, scale=4),
                  nullable=False, server_default='0'),
        sa.Column('net_correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Numeric(precision=10, scale=2),
                  nullable=False, server_default='0'),
        sa.Column('computed_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('explanation', postgresql.JSONB(), nullable=True),
    )

    # ── Flags Table ───────────────────────────────────────────
    op.create_table(
        'flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('attempts.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # Index for looking up flags by attempt
    op.create_index('ix_flags_attempt_id', 'flags', ['attempt_id'])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_index('ix_flags_attempt_id', table_name='flags')
    op.drop_table('flags')
    op.drop_table('attempt_scores')
    op.drop_index('ix_attempts_source_event_id', table_name='attempts')
    op.drop_index('ix_attempts_started_at', table_name='attempts')
    op.drop_index('ix_attempts_status', table_name='attempts')
    op.drop_index('ix_attempts_test_id', table_name='attempts')
    op.drop_index('ix_attempts_student_id', table_name='attempts')
    op.drop_table('attempts')
    op.drop_table('tests')
    op.drop_table('students')
