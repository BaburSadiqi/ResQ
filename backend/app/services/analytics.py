
from typing import Any

from app.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    async def get_summary(self) -> dict[str, Any]:
        return await self.repository.get_summary()
