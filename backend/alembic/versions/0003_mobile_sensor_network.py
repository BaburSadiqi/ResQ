"""add mobile sensor network tables

Revision ID: 0003_mobile_sensor_network
Revises: 0002_align_current_models
Create Date: 2026-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_mobile_sensor_network"
down_revision = "0002_align_current_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("mobile_devices", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True), sa.Column("manufacturer", sa.String(120)), sa.Column("model", sa.String(160)), sa.Column("android_version", sa.String(80)), sa.Column("sensor_name", sa.String(200)), sa.Column("sensor_vendor", sa.String(160)), sa.Column("sensor_resolution", sa.Float()), sa.Column("sensor_maximum_range", sa.Float()), sa.Column("app_version", sa.String(80)), sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_mobile_devices_device_id", "mobile_devices", ["device_id"])
    op.create_index("ix_mobile_devices_last_seen", "mobile_devices", ["last_seen"])
    op.create_table("sensor_reports", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mobile_devices.device_id", ondelete="CASCADE"), nullable=False), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("duration_ms", sa.Integer(), nullable=False), sa.Column("sample_count", sa.Integer(), nullable=False), sa.Column("sampling_rate_hz", sa.Float(), nullable=False), sa.Column("motion_state", sa.String(32), nullable=False), sa.Column("peak_acceleration", sa.Float(), nullable=False), sa.Column("rms_acceleration", sa.Float(), nullable=False), sa.Column("sensor_type", sa.String(80), nullable=False))
    op.create_index("ix_sensor_reports_device_id", "sensor_reports", ["device_id"])
    op.create_index("ix_sensor_reports_recorded_at", "sensor_reports", ["recorded_at"])
    op.create_index("ix_sensor_reports_received_at", "sensor_reports", ["received_at"])
    op.create_index("ix_sensor_reports_device_recorded", "sensor_reports", ["device_id", "recorded_at"])


def downgrade() -> None:
    op.drop_table("sensor_reports")
    op.drop_table("mobile_devices")
