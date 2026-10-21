
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
