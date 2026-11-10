import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.v1.endpoints.mobile import create_correlated_event_if_ready
from app.models.mobile import CorrelatedVibrationEvent, SensorReport


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, reports, latest=None):
        self.reports, self.latest, self.added = reports, latest, []

    async def scalars(self, query):
        return FakeScalars(self.reports)

    async def scalar(self, query):
        return self.latest

    def add(self, value):
        self.added.append(value)


def report(device_id, recorded_at):
    return SensorReport(
        device_id=device_id, recorded_at=recorded_at, motion_state="STRONG_VIBRATION",
        duration_ms=1000, sample_count=50, sampling_rate_hz=50, peak_acceleration=5.0,
        rms_acceleration=2.0, sensor_type="accelerometer",
    )


@pytest.mark.asyncio
async def test_one_strong_report_does_not_correlate():
    device = uuid.uuid4(); current = datetime.now(UTC)
    session = FakeSession([report(device, current)])
    await create_correlated_event_if_ready(session, session.reports[0])
    assert session.added == []


@pytest.mark.asyncio
async def test_repeated_reports_from_one_device_do_not_correlate():
    device = uuid.uuid4(); current = datetime.now(UTC)
    reports = [report(device, current), report(device, current - timedelta(seconds=1))]
    session = FakeSession(reports)
    await create_correlated_event_if_ready(session, reports[0])
    assert session.added == []


@pytest.mark.asyncio
async def test_two_distinct_devices_within_window_create_one_event():
    current = datetime.now(UTC); reports = [report(uuid.uuid4(), current), report(uuid.uuid4(), current - timedelta(seconds=2))]
    session = FakeSession(reports)
    await create_correlated_event_if_ready(session, reports[0])
    assert len(session.added) == 1
    assert isinstance(session.added[0], CorrelatedVibrationEvent)
    assert session.added[0].device_count == 2


@pytest.mark.asyncio
async def test_reports_outside_window_do_not_correlate():
    current = datetime.now(UTC); current_report = report(uuid.uuid4(), current); outside = report(uuid.uuid4(), current - timedelta(seconds=4))
    session = FakeSession([outside])
    await create_correlated_event_if_ready(session, current_report)
    assert session.added == []


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_event():
    current = datetime.now(UTC); reports = [report(uuid.uuid4(), current), report(uuid.uuid4(), current - timedelta(seconds=1))]
    latest = CorrelatedVibrationEvent(created_at=current - timedelta(seconds=5), participant_device_ids=[], trigger_timestamps=[], device_count=2, maximum_peak=5, correlation_window_seconds=3)
    session = FakeSession(reports, latest)
    await create_correlated_event_if_ready(session, reports[0])
    assert session.added == []
