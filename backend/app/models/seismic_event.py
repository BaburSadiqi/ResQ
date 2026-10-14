import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource


class SeismicEvent(Base):
    __tablename__ = "seismic_events"
    __table_args__ = (
        UniqueConstraint("data_source_id", "source_event_id", name="uq_event_source_external_id"),
        Index("ix_seismic_events_occurred_at", "occurred_at"),
        Index("ix_seismic_events_magnitude", "magnitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_event_id: Mapped[str] = mapped_column(String(200))
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    magnitude: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    magnitude_type: Mapped[str | None] = mapped_column(String(20))
    place: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    depth_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    event_type: Mapped[str | None] = mapped_column(String(50))
    source_status: Mapped[str | None] = mapped_column(String(40))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_url: Mapped[str | None] = mapped_column(String(1000))
    raw_properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    data_source: Mapped["DataSource"] = relationship(back_populates="seismic_events")
