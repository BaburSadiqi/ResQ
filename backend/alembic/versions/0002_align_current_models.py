"""align schema with current models

Revision ID: 0002_align_current_models
Revises: 0001_foundation
Create Date: 2026-10-18
"""
import sqlalchemy as sa

from alembic import op

revision = "0002_align_current_models"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_data_sources_name", table_name="data_sources")
    op.drop_index("ix_data_sources_source_type", table_name="data_sources")
    op.drop_constraint("data_sources_name_key", "data_sources", type_="unique")

    op.add_column("data_sources", sa.Column("code", sa.String(length=50), nullable=True))
    op.execute(
        "UPDATE data_sources "
        "SET code = 'source-' || replace(id::text, '-', '')"
    )
    op.execute(
        "UPDATE data_sources "
        "SET code = 'usgs' "
        "WHERE id = ("
        "SELECT id FROM data_sources "
        "WHERE lower(name) LIKE '%usgs%' "
        "ORDER BY id LIMIT 1"
        ")"
    )
    op.alter_column("data_sources", "code", nullable=False)
    op.create_index("ix_data_sources_code", "data_sources", ["code"], unique=True)

    op.alter_column("data_sources", "is_enabled", new_column_name="is_active")
    op.alter_column("data_sources", "base_url", existing_type=sa.String(length=500), nullable=True)
    op.drop_column("data_sources", "source_type")

    op.drop_constraint(
        "seismic_events_data_source_id_fkey", "seismic_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "seismic_events_data_source_id_fkey",
        "seismic_events",
        "data_sources",
        ["data_source_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("seismic_events", "event_status", new_column_name="source_status")
    op.alter_column("seismic_events", "source_url", new_column_name="event_url")
    op.add_column(
        "seismic_events", sa.Column("event_type", sa.String(length=50), nullable=True)
    )
    op.create_index("ix_seismic_events_magnitude", "seismic_events", ["magnitude"])


def downgrade() -> None:
    op.drop_index("ix_seismic_events_magnitude", table_name="seismic_events")
    op.drop_column("seismic_events", "event_type")
    op.alter_column("seismic_events", "event_url", new_column_name="source_url")
    op.alter_column("seismic_events", "source_status", new_column_name="event_status")
    op.drop_constraint(
        "seismic_events_data_source_id_fkey", "seismic_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "seismic_events_data_source_id_fkey",
        "seismic_events",
        "data_sources",
        ["data_source_id"],
        ["id"],
    )

    op.add_column(
        "data_sources",
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="seismic"),
    )
    op.alter_column("data_sources", "source_type", server_default=None)
    op.execute("UPDATE data_sources SET base_url = '' WHERE base_url IS NULL")
    op.alter_column("data_sources", "base_url", existing_type=sa.String(length=500), nullable=False)
    op.alter_column("data_sources", "is_active", new_column_name="is_enabled")
    op.drop_index("ix_data_sources_code", table_name="data_sources")
    op.drop_column("data_sources", "code")

    op.create_unique_constraint("data_sources_name_key", "data_sources", ["name"])
    op.create_index("ix_data_sources_name", "data_sources", ["name"])
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"])