from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field


class EarthquakeScenarioRequest(BaseModel):
    """A hypothetical earthquake input used only for research analysis."""

    latitude: Annotated[
        Decimal,
        Field(ge=-90, le=90, description="Hypothetical latitude in WGS 84 decimal degrees."),
    ]
    longitude: Annotated[
        Decimal,
        Field(ge=-180, le=180, description="Hypothetical longitude in WGS 84 decimal degrees."),
    ]
    magnitude: Annotated[
        Decimal,
        Field(ge=-2, le=10, description="Hypothetical magnitude on the catalog magnitude scale."),
    ]
    depth_km: Annotated[
        Decimal,
        Field(ge=0, le=700, description="Hypothetical focal depth in kilometers."),
    ]
    radius_km: Annotated[
        Decimal,
        Field(
            ge=1,
            le=20015,
            description=(
                "Historical-catalog search radius in kilometers, up to an antipodal distance."
            ),
        ),
    ]


class HistoricalCatalogProximitySummary(BaseModel):
    """Aggregates of observed catalog events near the hypothetical location.

    Magnitude statistics exclude catalog events with null magnitude. Distance
    statistics include every matching observed catalog event.
    """

    events_within_radius: int
    events_with_magnitude: int
    events_without_magnitude: int
    smallest_magnitude: Decimal | None
    largest_magnitude: Decimal | None
    average_magnitude: Decimal | None
    nearest_distance_km: Decimal | None
    farthest_distance_km: Decimal | None
    average_distance_km: Decimal | None


class EarthquakeScenarioSimulation(BaseModel):
    """A research-only comparison of a hypothetical input with observed catalog data."""

    scenario: EarthquakeScenarioRequest
    historical_catalog: HistoricalCatalogProximitySummary
