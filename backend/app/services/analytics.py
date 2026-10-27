
from decimal import Decimal
from typing import Any

from app.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    async def get_summary(self) -> dict[str, Any]:
        return await self.repository.get_summary()

    async def get_geographic_summary(
        self, south: Decimal, north: Decimal, west: Decimal, east: Decimal
    ) -> dict[str, Any]:
        return await self.repository.get_geographic_summary(south, north, west, east)
