from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seismic_event import SeismicEvent


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary(self) -> dict[str, Any]:
        magnitude = SeismicEvent.magnitude

        statement = select(
            func.count(SeismicEvent.id).label("total_events"),
            func.count(magnitude).label("events_with_magnitude"),
            func.max(magnitude).label("largest_magnitude"),
            func.avg(magnitude).label("average_magnitude"),
            func.count(
                case((magnitude < 2.0, 1))
            ).label("micro"),
            func.count(
                case((magnitude >= 2.0, 1))
            ).label("magnitude_2_plus"),
            func.count(
                case((magnitude >= 4.0, 1))
            ).label("magnitude_4_plus"),
            func.count(
                case((magnitude >= 5.0, 1))
            ).label("magnitude_5_plus"),
        )

        result = await self.session.execute(statement)
        row = result.one()

        return {
            "total_events": row.total_events,
            "events_with_magnitude": row.events_with_magnitude,
            "largest_magnitude": row.largest_magnitude,
            "average_magnitude": (
                Decimal(str(row.average_magnitude))
                if row.average_magnitude is not None
                else None
            ),
            "magnitude_distribution": {
                "below_2": row.micro,
                "from_2_to_below_4": (
                    row.magnitude_2_plus - row.magnitude_4_plus
                ),
                "from_4_to_below_5": (
                    row.magnitude_4_plus - row.magnitude_5_plus
                ),
                "above_or_equal_5": row.magnitude_5_plus,
            },
        }

        
