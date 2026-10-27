
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MagnitudeDistribution(BaseModel):
    below_2: int
    from_2_to_below_4: int
    from_4_to_below_5: int
    above_or_equal_5: int


class AnalyticsSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_events: int
    events_with_magnitude: int
    largest_magnitude: Decimal | None
    average_magnitude: Decimal | None
    magnitude_distribution: MagnitudeDistribution


class GeographicBoundsQuery(BaseModel):
    """A geographic bounding box in WGS 84 decimal degrees."""

    south: Annotated[Decimal, Field(ge=-90, le=90)]
    north: Annotated[Decimal, Field(ge=-90, le=90)]
    west: Annotated[Decimal, Field(ge=-180, le=180)]
    east: Annotated[Decimal, Field(ge=-180, le=180)]

    @model_validator(mode="after")
    def validate_latitude_range(self) -> "GeographicBoundsQuery":
        if self.south > self.north:
            raise ValueError("south must be less than or equal to north")
        return self


class GeographicBounds(BaseModel):
    """The bounding box applied to the stored catalog query."""

    south: Decimal
    north: Decimal
    west: Decimal
    east: Decimal
    crosses_antimeridian: bool


class GeographicAnalyticsSummary(BaseModel):
    """Observed catalog aggregates for one geographic bounding box.

    Magnitude statistics exclude events whose catalog magnitude is null. The
    total event count includes them, and ``events_without_magnitude`` reports
    their number separately.
    """

    bounds: GeographicBounds
    total_events: int
    events_with_magnitude: int
    events_without_magnitude: int
    smallest_magnitude: Decimal | None
    largest_magnitude: Decimal | None
    average_magnitude: Decimal | None
