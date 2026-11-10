# Copilot instructions

## Build, test, and lint

- Backend (from `backend/`): `./mvnw package` builds and runs the Maven test suite. Run the app with `./mvnw spring-boot:run`.
- Run one backend test with `./mvnw -Dtest=F1DataPlatformApplicationTests#contextLoads test` from `backend/`; replace the class and method with the test you want.
- The Spring application and context test use PostgreSQL and Flyway. Start the database from the repository root with `docker compose up -d postgres`; create a root `.env` from `.env.example` and set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` before starting the database or backend.
- Frontend (from `frontend/`): `npm run build:css` builds Tailwind CSS to `dist/output.css`; `npm run watch:css` watches for changes. The `npm test` script is only a placeholder and exits with an error.
- There is no configured lint command or linter in the backend, frontend, or Python pipeline.
- To inspect local CSV metadata, install `data-pipeline/requirements.txt` and run `python inspect_raw.py` from `data-pipeline/`. It reads CSVs in `data-pipeline/raw/`; it is an inspection utility, not a data-loading pipeline.

## Architecture

The intended product flow in `README.md` is historical F1 data ingestion and transformation, PostgreSQL storage, a Spring Boot REST/JSON API, and a browser dashboard. Treat that as the target architecture, not a claim that every component is implemented.

Currently, `data-pipeline/inspect_raw.py` reports metadata and duplicate counts for raw CSVs; there is not yet an implemented ETL/loading workflow. `backend/` is a Spring Boot application with JPA, validation, and web dependencies. `frontend/` is a minimal static HTML page styled with Tailwind CSS. `docker-compose.yml` currently starts only PostgreSQL.

The initial PostgreSQL schema is defined in `backend/src/main/resources/db/migration/V1__init_schema.sql`. It normalizes source data into related reference, race/session, result/standing, lap, and pit-stop tables. `application.properties` configures Flyway and sets Hibernate to validate the schema, so the migration is the source of truth for database structure. The README's endpoint examples and dashboard views are planned capabilities; don't assume controllers, repositories, or data ingestion already exist.

## Repository conventions

- Add database changes as new ordered Flyway migrations under `backend/src/main/resources/db/migration/`, named `V<number>__<description>.sql`; do not rely on Hibernate to create or update tables.
- Preserve Ergast source IDs as primary keys where the schema uses them. Schema names use `snake_case`; the relational model uses foreign keys, uniqueness constraints, and nullable columns for historically absent values.
- Keep backend Java classes under `com.lucamonaco.f1dataplatform` in the matching package directory.
- Frontend styles are authored in `frontend/src/input.css` using Tailwind v4's `@import "tailwindcss";`; the build output is `frontend/dist/output.css`.
- Local database credentials are supplied through the root `.env`, which is ignored by Git. The backend imports it as an optional properties file; don't commit local credentials.
- Raw and processed data directories are intentionally ignored by Git. The CSV inspection script expects raw files under `data-pipeline/raw/`.
