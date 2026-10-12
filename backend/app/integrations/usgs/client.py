from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalDataError


class UsgsClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings, self._client = settings, client

    async def fetch_events(self, start_time: datetime, end_time: datetime, min_magnitude: float | None = None) -> list[dict[str, Any]]:
        params: dict[str, str | float] = {"format": "geojson", "starttime": start_time.isoformat(), "endtime": end_time.isoformat()}
        if min_magnitude is not None:
            params["minmagnitude"] = min_magnitude
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(self.settings.http_timeout_seconds))
        try:
            response = await client.get(f"{str(self.settings.usgs_base_url).rstrip('/')}/query", params=params)
            response.raise_for_status()
            payload = response.json()
            features = payload.get("features") if isinstance(payload, dict) else None
            if not isinstance(features, list):
                raise ExternalDataError("USGS response did not contain GeoJSON features")
            return features
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalDataError("USGS catalog request failed") from exc
        finally:
            if owns_client:
                await client.aclose()
