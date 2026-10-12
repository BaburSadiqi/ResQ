"""Explicit bounded USGS catalog import; never runs automatically."""
import argparse
import asyncio
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.usgs.client import UsgsClient
from app.services.ingestion import UsgsIngestionService


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include a UTC offset, e.g. 2025-01-01T00:00:00Z")
    return parsed.astimezone(UTC)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import a bounded USGS earthquake catalog time range.")
    parser.add_argument("start_time", type=parse_utc)
    parser.add_argument("end_time", type=parse_utc)
    parser.add_argument("--min-magnitude", type=float)
    args = parser.parse_args()
    if args.start_time >= args.end_time:
        parser.error("start_time must be before end_time")
    async with SessionLocal() as session:
        count = await UsgsIngestionService(session, UsgsClient(get_settings())).ingest(args.start_time, args.end_time, args.min_magnitude)
    print(f"Imported {count} new USGS catalog event(s).")


if __name__ == "__main__":
    asyncio.run(main())
