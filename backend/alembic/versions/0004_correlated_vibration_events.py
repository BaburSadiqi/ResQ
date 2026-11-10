"""add correlated vibration research events

Revision ID: 0004_correlated_vibration_events
Revises: 0003_mobile_sensor_network
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_correlated_vibration_events"
down_revision = "0003_mobile_sensor_network"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correlated_vibration_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("participant_device_ids", postgresql.JSONB(), nullable=False),
        sa.Column("trigger_timestamps", postgresql.JSONB(), nullable=False),
        sa.Column("device_count", sa.Integer(), nullable=False),
        sa.Column("maximum_peak", sa.Float(), nullable=False),
        sa.Column("correlation_window_seconds", sa.Float(), nullable=False),
    )
    op.create_index("ix_correlated_vibration_events_created_at", "correlated_vibration_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("correlated_vibration_events")
