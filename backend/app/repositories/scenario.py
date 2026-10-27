import math
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seismic_event import SeismicEvent

EARTH_RADIUS_KM = 6371.0088


class ScenarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_historical_proximity_summary(
        self, latitude: Decimal, longitude: Decimal, radius_km: Decimal
    ) -> dict[str, Any]:
        """Aggregate stored events within a great-circle radius in PostgreSQL."""
        radius = float(radius_km)
        latitude_delta = math.degrees(radius / EARTH_RADIUS_KM)
        candidate_south = max(-90, float(latitude) - latitude_delta)
        candidate_north = min(90, float(latitude) + latitude_delta)

        event_latitude = func.radians(SeismicEvent.latitude)
        event_longitude = func.radians(SeismicEvent.longitude)
        target_latitude = math.radians(float(latitude))
        target_longitude = math.radians(float(longitude))
        haversine_term = (
            func.pow(func.sin((event_latitude - target_latitude) / 2), 2)
            + func.cos(target_latitude)
            * func.cos(event_latitude)
            * func.pow(func.sin((event_longitude - target_longitude) / 2), 2)
        )
        distance_km = (
            2
            * EARTH_RADIUS_KM
            * func.asin(func.sqrt(func.least(1.0, func.greatest(0.0, haversine_term))))
        )
        magnitude = SeismicEvent.magnitude
        statement = select(
            func.count(SeismicEvent.id).label("events_within_radius"),
            func.count(magnitude).label("events_with_magnitude"),
            func.min(magnitude).label("smallest_magnitude"),
            func.max(magnitude).label("largest_magnitude"),
            func.avg(magnitude).label("average_magnitude"),
            func.min(distance_km).label("nearest_distance_km"),
            func.max(distance_km).label("farthest_distance_km"),
            func.avg(distance_km).label("average_distance_km"),
        ).where(
            SeismicEvent.latitude.between(candidate_south, candidate_north),
            distance_km <= radius,
        )
        row = (await self.session.execute(statement)).one()
        events_with_magnitude = row.events_with_magnitude

        return {
            "events_within_radius": row.events_within_radius,
            "events_with_magnitude": events_with_magnitude,
            "events_without_magnitude": row.events_within_radius - events_with_magnitude,
            "smallest_magnitude": self._decimal_or_none(row.smallest_magnitude),
            "largest_magnitude": self._decimal_or_none(row.largest_magnitude),
            "average_magnitude": self._decimal_or_none(row.average_magnitude),
            "nearest_distance_km": self._decimal_or_none(row.nearest_distance_km),
            "farthest_distance_km": self._decimal_or_none(row.farthest_distance_km),
            "average_distance_km": self._decimal_or_none(row.average_distance_km),
        }

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None
