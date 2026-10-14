import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.v1.endpoints.seismic_events import get_service
from app.db.session import get_session
from app.main import app
from app.models.seismic_event import SeismicEvent


class FakeService:
    def __init__(self, event: SeismicEvent | None) -> None:
        self.event = event

    async def list(self, limit: int, offset: int, min_magnitude: float | None, start_time: datetime | None, end_time: datetime | None):
        assert limit == 2
        assert min_magnitude == 4
        return ([self.event] if self.event else []), 1 if self.event else 0

    async def get(self, event_id: uuid.UUID):
        return self.event if self.event and event_id == self.event.id else None


def sample_event() -> SeismicEvent:
    return SeismicEvent(id=uuid.uuid4(), source_event_id="us1", data_source_id=uuid.uuid4(), magnitude=Decimal("4.20"), magnitude_type="mb", place="Test", latitude=Decimal("34.5"), longitude=Decimal("67.1"), depth_km=Decimal("10"), event_type="earthquake", source_status="reviewed", occurred_at=datetime.now(UTC), source_updated_at=None, event_url=None, raw_properties={})


def test_health() -> None:
    assert TestClient(app).get("/api/v1/health").json() == {"status": "ok", "database": None}


def test_readiness_reports_database_failure() -> None:
    class UnavailableSession:
        async def execute(self, query):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    async def unavailable_session():
        yield UnavailableSession()

    app.dependency_overrides[get_session] = unavailable_session
    try:
        assert TestClient(app).get("/api/v1/health/ready").status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_event_filtering_and_not_found() -> None:
    event = sample_event()
    app.dependency_overrides[get_service] = lambda: FakeService(event)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/seismic-events?limit=2&min_magnitude=4")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert client.get(f"/api/v1/seismic-events/{uuid.uuid4()}").status_code == 404
    finally:
        app.dependency_overrides.clear()
