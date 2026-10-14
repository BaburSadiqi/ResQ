from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

from app.models.data_source import DataSource
from app.models.seismic_event import SeismicEvent


def test_data_source_metadata_and_relationship() -> None:
    table = DataSource.__table__

    assert table.c.code.unique is True
    assert table.c.base_url.nullable is True
    assert table.c.is_active.nullable is False
    assert inspect(DataSource).relationships["seismic_events"].mapper.class_ is SeismicEvent


def test_seismic_event_metadata_constraints_indexes_and_relationship() -> None:
    table = SeismicEvent.__table__
    foreign_key = next(iter(table.c.data_source_id.foreign_keys))

    assert foreign_key.ondelete == "RESTRICT"
    assert table.c.occurred_at.type.timezone is True
    assert table.c.raw_properties.type.__class__ is JSONB
    assert {index.name for index in table.indexes} >= {
        "ix_seismic_events_occurred_at",
        "ix_seismic_events_magnitude",
    }
    assert any(
        constraint.name == "uq_event_source_external_id"
        and tuple(column.name for column in constraint.columns)
        == ("data_source_id", "source_event_id")
        for constraint in table.constraints
    )
    assert inspect(SeismicEvent).relationships["data_source"].mapper.class_ is DataSource
