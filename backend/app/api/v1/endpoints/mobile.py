from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.mobile import MobileDevice, SensorReport
from app.schemas.mobile import (DeviceRegistration, DeviceResponse, MobileHealthResponse,
    RegistrationResponse, SensorReportCreate, SensorReportResponse)

router = APIRouter(prefix="/mobile", tags=["mobile sensor network"])
ONLINE_WINDOW = timedelta(seconds=30)


def report_response(report: SensorReport) -> SensorReportResponse:
    return SensorReportResponse.model_validate(report, from_attributes=True)


@router.get("/health", response_model=MobileHealthResponse)
async def mobile_health() -> MobileHealthResponse:
    return MobileHealthResponse()


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
