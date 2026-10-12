"""foundation tables

Revision ID: 0001_foundation
Revises:
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("data_sources", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("base_url", sa.String(500), nullable=False), sa.Column("source_type", sa.String(40), nullable=False), sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_data_sources_name", "data_sources", ["name"])
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"])
    op.create_table("seismic_events", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("source_event_id", sa.String(200), nullable=False), sa.Column("data_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id"), nullable=False), sa.Column("magnitude", sa.Numeric(4, 2)), sa.Column("magnitude_type", sa.String(20)), sa.Column("place", sa.String(500)), sa.Column("latitude", sa.Numeric(9, 6), nullable=False), sa.Column("longitude", sa.Numeric(9, 6), nullable=False), sa.Column("depth_km", sa.Numeric(8, 3)), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("source_updated_at", sa.DateTime(timezone=True)), sa.Column("event_status", sa.String(40)), sa.Column("source_url", sa.String(1000)), sa.Column("raw_properties", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("data_source_id", "source_event_id", name="uq_event_source_external_id"))
    op.create_index("ix_seismic_events_data_source_id", "seismic_events", ["data_source_id"])
    op.create_index("ix_seismic_events_occurred_at", "seismic_events", ["occurred_at"])

def downgrade() -> None:
    op.drop_table("seismic_events")
    op.drop_table("data_sources")
