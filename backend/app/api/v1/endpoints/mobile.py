from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.mobile import CorrelatedVibrationEvent, MobileDevice, SensorReport
from app.schemas.mobile import (DeviceRegistration, DeviceResponse, MobileHealthResponse,
    CorrelatedVibrationAlert, RegistrationResponse, SensorReportCreate, SensorReportResponse)

router = APIRouter(prefix="/mobile", tags=["mobile sensor network"])
ONLINE_WINDOW = timedelta(seconds=30)
CORRELATION_WINDOW = timedelta(seconds=3)
CORRELATION_COOLDOWN = timedelta(seconds=10)


async def create_correlated_event_if_ready(session: AsyncSession, report: SensorReport) -> None:
    if report.motion_state != "STRONG_VIBRATION":
        return
    now = datetime.now(UTC)
    recent = (await session.scalars(
        select(SensorReport)
        .where(
            SensorReport.motion_state == "STRONG_VIBRATION",
            SensorReport.recorded_at >= report.recorded_at - CORRELATION_WINDOW,
            SensorReport.recorded_at <= report.recorded_at + CORRELATION_WINDOW,
        )
        .order_by(SensorReport.recorded_at.desc())
    )).all()
    by_device: dict[str, SensorReport] = {}
    for candidate in recent:
        by_device.setdefault(str(candidate.device_id), candidate)
    if len(by_device) < 2:
        return
    latest_event = await session.scalar(
        select(CorrelatedVibrationEvent)
        .order_by(CorrelatedVibrationEvent.created_at.desc())
        .limit(1)
    )
    if latest_event and latest_event.created_at and now - latest_event.created_at < CORRELATION_COOLDOWN:
        return
    participants = list(by_device.values())
    event = CorrelatedVibrationEvent(
        participant_device_ids=list(by_device),
        trigger_timestamps=[item.recorded_at.isoformat() for item in participants],
        device_count=len(participants),
        maximum_peak=max(item.peak_acceleration for item in participants),
        correlation_window_seconds=CORRELATION_WINDOW.total_seconds(),
    )
    session.add(event)


def report_response(report: SensorReport) -> SensorReportResponse:
    return SensorReportResponse.model_validate(report, from_attributes=True)


@router.get("/health", response_model=MobileHealthResponse)
async def mobile_health() -> MobileHealthResponse:
    return MobileHealthResponse()


@router.get("/devices/{device_id}/alerts/latest", response_model=CorrelatedVibrationAlert | None)
async def latest_alert(device_id: UUID, session: AsyncSession = Depends(get_session)) -> CorrelatedVibrationAlert | None:
    events = (await session.scalars(
        select(CorrelatedVibrationEvent)
        .where(CorrelatedVibrationEvent.created_at >= datetime.now(UTC) - timedelta(minutes=10))
        .order_by(CorrelatedVibrationEvent.created_at.desc())
        .limit(20)
    )).all()
    for event in events:
        if str(device_id) in event.participant_device_ids:
            return CorrelatedVibrationAlert(
                event_id=event.id, created_at=event.created_at, device_count=event.device_count,
                participant_device_ids=[UUID(value) for value in event.participant_device_ids],
                trigger_timestamps=[datetime.fromisoformat(value) for value in event.trigger_timestamps],
                maximum_peak=event.maximum_peak,
                correlation_window_seconds=event.correlation_window_seconds,
            )
    return None


@router.get("/correlated-events/latest", response_model=CorrelatedVibrationAlert | None)
async def latest_correlated_event(session: AsyncSession = Depends(get_session)) -> CorrelatedVibrationAlert | None:
    event = await session.scalar(select(CorrelatedVibrationEvent).order_by(CorrelatedVibrationEvent.created_at.desc()).limit(1))
    if event is None:
        return None
    return CorrelatedVibrationAlert(
        event_id=event.id, created_at=event.created_at, device_count=event.device_count,
        participant_device_ids=[UUID(value) for value in event.participant_device_ids],
        trigger_timestamps=[datetime.fromisoformat(value) for value in event.trigger_timestamps],
        maximum_peak=event.maximum_peak, correlation_window_seconds=event.correlation_window_seconds,
    )


@router.post("/devices/register", response_model=RegistrationResponse)
async def register_device(payload: DeviceRegistration, session: AsyncSession = Depends(get_session)) -> RegistrationResponse:
    now = datetime.now(UTC)
    device = await session.scalar(select(MobileDevice).where(MobileDevice.device_id == payload.device_id))
    if device is None:
        device = MobileDevice(**payload.model_dump(), last_seen=now)
        session.add(device)
    else:
        for key, value in payload.model_dump().items():
            setattr(device, key, value)
        device.last_seen = now
    await session.commit()
    return RegistrationResponse(device_id=device.device_id, last_seen=device.last_seen)


@router.post("/devices/{device_id}/heartbeat", response_model=RegistrationResponse)
async def heartbeat(device_id: UUID, session: AsyncSession = Depends(get_session)) -> RegistrationResponse:
    device = await session.scalar(select(MobileDevice).where(MobileDevice.device_id == device_id))
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown device")
    device.last_seen = datetime.now(UTC)
    await session.commit()
    return RegistrationResponse(device_id=device.device_id, last_seen=device.last_seen)


@router.post("/sensor-reports", response_model=SensorReportResponse, status_code=status.HTTP_201_CREATED)
async def create_sensor_report(payload: SensorReportCreate, session: AsyncSession = Depends(get_session)) -> SensorReportResponse:
    device = await session.scalar(select(MobileDevice).where(MobileDevice.device_id == payload.device_id))
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown device")
    report = SensorReport(**payload.model_dump())
    device.last_seen = datetime.now(UTC)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    await create_correlated_event_if_ready(session, report)
    await session.commit()
    return report_response(report)


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(session: AsyncSession = Depends(get_session)) -> list[DeviceResponse]:
    devices = (await session.scalars(select(MobileDevice).order_by(MobileDevice.last_seen.desc()))).all()
    now = datetime.now(UTC)
    result = []
    for device in devices:
        latest = await session.scalar(select(SensorReport).where(SensorReport.device_id == device.device_id).order_by(SensorReport.received_at.desc()).limit(1))
        result.append(DeviceResponse.model_validate({**{key: getattr(device, key) for key in DeviceResponse.model_fields if key not in {"online", "latest_report"}}, "online": now - device.last_seen <= ONLINE_WINDOW, "latest_report": report_response(latest) if latest else None}))
    return result


@router.get("/sensor-reports/recent", response_model=list[SensorReportResponse])
async def recent_reports(limit: int = Query(default=50, ge=1, le=200), session: AsyncSession = Depends(get_session)) -> list[SensorReportResponse]:
    reports = (await session.scalars(select(SensorReport).order_by(SensorReport.received_at.desc()).limit(limit))).all()
    return [report_response(report) for report in reports]
