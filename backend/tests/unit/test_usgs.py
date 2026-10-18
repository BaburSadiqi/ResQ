import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ExternalDataError
from app.integrations.usgs.client import UsgsClient
from app.integrations.usgs.schemas import UsgsEvent
from app.models.data_source import DataSource
from app.services.ingestion import UsgsIngestionService


def feature() -> dict:
    return {"id": "us123", "geometry": {"coordinates": [67.1, 34.5, 10]}, "properties": {"time": 1_700_000_000_000, "updated": 1_700_000_100_000, "mag": 4.2, "magType": "mb", "place": "test", "status": "reviewed", "url": "https://example.org/event"}}


def test_normalizes_geojson_to_utc() -> None:
    event = UsgsEvent.model_validate(feature())
    assert event.occurred_at.tzinfo == UTC
    assert event.source_event_id == "us123"


def test_rejects_incomplete_feature() -> None:
    with pytest.raises(ValueError):
        UsgsEvent.model_validate({"id": "missing"})


@pytest.mark.asyncio
async def test_http_error_is_wrapped() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, request=request))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ExternalDataError):
            await UsgsClient(Settings(), client).fetch_events(datetime.now(UTC), datetime.now(UTC))


@pytest.mark.asyncio
async def test_timeout_is_wrapped() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ExternalDataError):
            await UsgsClient(Settings(), client).fetch_events(datetime.now(UTC), datetime.now(UTC))


@pytest.mark.asyncio
async def test_empty_geojson_response_returns_no_events() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        result = await UsgsClient(Settings(), client).fetch_events(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )
    assert result == []


@pytest.mark.asyncio
async def test_malformed_records_are_skipped() -> None:
    source = DataSource(name="USGS Earthquake Catalog", code="usgs")
    source.id = uuid.uuid4()

    class Session:
        async def scalar(self, query):
            return source if "data_sources" in str(query) else None

        def add(self, item) -> None:
            raise AssertionError("no malformed event should be added")

        async def commit(self) -> None:
            pass

    class Client:
        settings = Settings()

        async def fetch_events(self, *args):
            return [{"id": "bad", "properties": {}, "geometry": {"coordinates": []}}]

    assert await UsgsIngestionService(Session(), Client()).ingest(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
    ) == 0


@pytest.mark.asyncio
async def test_duplicate_catalog_event_is_not_added() -> None:
    source = DataSource(name="USGS Earthquake Catalog", code="usgs", base_url="https://example.org")
    source.id = uuid.uuid4()

    class Session:
        def __init__(self) -> None:
            self.calls = 0
            self.added = []

        async def scalar(self, query):
            self.calls += 1
            return source if self.calls == 1 else None

        def add(self, item) -> None:
            self.added.append(item)

        async def commit(self) -> None:
            pass

    class Client:
        settings = Settings()

        async def fetch_events(self, *args):
            return [feature()]

    session = Session()
    count = await UsgsIngestionService(session, Client()).ingest(datetime.now(UTC), datetime.now(UTC))
    assert count == 0
    assert session.added == []
