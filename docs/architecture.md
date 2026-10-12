# Architecture

ResQ uses a layered FastAPI design: routes validate HTTP input and serialize output; services coordinate work; repositories contain SQLAlchemy queries; integrations communicate with external providers; models map PostgreSQL entities; schemas are Pydantic contracts.

`USGS GeoJSON -> UsgsClient -> UsgsIngestionService -> PostgreSQL -> repository/service -> API`

The application never contacts USGS or creates database tables at startup. Database schema changes are reviewed Alembic migrations.
