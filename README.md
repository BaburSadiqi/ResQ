# ResQ

> Earthquake Early Warning Research & Simulation Platform

ResQ is an open-source university research prototype for exploring earthquake-event catalog workflows and controlled seismic simulations. It provides a reliable backend foundation for importing, storing, filtering, and studying public earthquake catalog data.

> [!IMPORTANT]
> ResQ does **not** predict earthquakes. Its USGS integration imports published catalog records; it is not a real-time seismic sensor network or a validated operational early-warning service.

## Features

- Async FastAPI API with OpenAPI/Swagger documentation
- PostgreSQL persistence through SQLAlchemy 2.0 and Alembic migrations
- Paginated seismic-event catalog API with time and magnitude filters
- Health and database-readiness endpoints
- Configurable, asynchronous USGS FDSN GeoJSON integration
- Explicit, bounded event ingestion command—no automatic polling
- Offline unit tests for API behavior, normalization, failures, and duplicate handling
- Clear separation between API routes, services, repositories, data models, and external integrations

## Scientific Scope and Limitations

Earthquakes cannot currently be predicted reliably before they occur. ResQ must not be presented as an earthquake prediction product.

USGS FDSN event records represent cataloged earthquakes that have been detected, located, and published. They are not early-warning detections. Any future simulations, experimental assessments, or validated alerts must be clearly identified as separate data categories.

See [docs/data-sources.md](docs/data-sources.md) for data provenance and limitations.

## Technology Stack

| Area | Technology |
| --- | --- |
| API | Python 3.12+, FastAPI, Uvicorn |
| Validation & settings | Pydantic v2, pydantic-settings |
| Database | PostgreSQL, SQLAlchemy 2.0 (async), asyncpg |
| Migrations | Alembic |
| External catalog | USGS FDSN Event Web Service (GeoJSON) |
| Quality | Pytest, pytest-asyncio, Ruff |
| Planned frontend | Next.js, TypeScript, Tailwind CSS, Leaflet |

## Project Structure

```text
ResQ/
├── backend/          # FastAPI application, migrations, and tests
├── docs/             # Architecture and data-source documentation
├── frontend/         # Reserved for the future web client
├── LICENSE           # MIT License
└── README.md
```

For layer boundaries and data flow, see [docs/architecture.md](docs/architecture.md).

## Getting Started (Windows)

### Prerequisites

- Python 3.12 or newer
- PostgreSQL
- PowerShell

### Install

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `backend/.env` with your local PostgreSQL credentials. Never commit this file.

### Create the database and run migrations

```powershell
psql -U postgres -h localhost -c "CREATE DATABASE resq;"
alembic upgrade head
```

### Run the API

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation at <http://127.0.0.1:8000/docs>.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Application health status |
| `GET` | `/api/v1/health/ready` | PostgreSQL connectivity check |
| `GET` | `/api/v1/seismic-events` | Persisted events with pagination and filters |
| `GET` | `/api/v1/seismic-events/{event_id}` | One persisted event by internal UUID |

Supported list filters are `limit`, `offset`, `min_magnitude`, `start_time`, and `end_time`.

## Import a Bounded USGS Catalog Range

After applying migrations, explicitly import a finite time range:

```powershell
python -m app.cli.ingest_usgs 2025-01-01T00:00:00Z 2025-01-02T00:00:00Z --min-magnitude 4.5
```

This command contacts USGS. It does not run automatically, and it does not create a continuous polling service.

## Development and Quality Checks

```powershell
pytest
ruff check .
ruff format --check .
```

## Roadmap

- Controlled, clearly labelled seismic simulations
- Experimental research assessments
- Next.js map-based frontend
- Carefully evaluated early-warning research workflows

## License

Copyright © 2026 Mohammad Babur Sadiqi.

This project is licensed under the [MIT License](LICENSE).
