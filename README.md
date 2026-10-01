# 🏎️ F1 Data Platform

## Overview

**F1 Data Platform** is a data processing and analytics platform designed to collect, transform, store, and expose Formula 1 racing data through a structured and queryable system.

The project focuses less on building a conventional "F1 website" and more on demonstrating how raw data can be transformed into a reliable data product through an automated processing pipeline.

The final result would be a publicly accessible web application where users can explore races, drivers, teams, lap times, stints, pit stops, and other historical data through interactive visualizations.

---

## Product

The platform would allow users to explore Formula 1 data at different levels.

A user could select:

* a season;
* a Grand Prix;
* a session;
* a driver;
* a team.

The application could then expose information such as:

* race results;
* qualifying results;
* lap times;
* fastest laps;
* tyre compounds;
* stints;
* pit stops;
* driver/team comparisons;
* lap-time evolution;
* position changes throughout a race.

The objective is not to compete with existing professional F1 statistics platforms. The product is primarily a **data engineering and analytics showcase**.

Its value comes from demonstrating how raw motorsport data can be ingested, cleaned, normalized, stored, queried, and presented through a coherent software system.

---

## Architecture

The system can be structured as a data pipeline followed by an API and a presentation layer.

```text
                    External Data Sources
                            │
                            ▼
                    Python Data Ingestion
                            │
                            ▼
                  Cleaning & Transformation
                            │
                            ▼
                       PostgreSQL
                            │
                            ▼
                     Spring Boot API
                            │
                    REST / JSON
                            │
                            ▼
                 Web Analytics Dashboard
```

### Data ingestion

Python would be responsible for retrieving the original data and transforming it into a consistent internal representation.

The ingestion layer should handle:

* downloading or reading raw datasets;
* validation;
* normalization;
* missing values;
* data type conversion;
* duplicate detection;
* transformation into database-ready structures.

The ingestion process should be reproducible rather than manually executed whenever new data is added.

For example:

```text
raw/
    races.csv
    drivers.csv
    lap_times.csv

        ↓

Python pipeline

        ↓

processed/
    races.parquet
    drivers.parquet
    lap_times.parquet

        ↓

PostgreSQL
```

The exact intermediate format can be changed depending on the final implementation.

### Database

PostgreSQL would provide the persistent storage layer.

A relational schema could contain entities such as:

```text
seasons
races
circuits
drivers
constructors
sessions
results
laps
stints
pit_stops
```

Relationships between these entities would allow the application to perform meaningful analytical queries without storing the same information repeatedly.

The database should be designed as an actual data model rather than simply mirroring the structure of the original data source.

### Backend

A Spring Boot application would expose the processed data through REST APIs.

Example endpoints:

```text
GET /api/seasons
GET /api/seasons/{year}/races
GET /api/races/{raceId}
GET /api/races/{raceId}/results
GET /api/races/{raceId}/laps/{driverId}
GET /api/drivers/{driverId}/statistics
GET /api/teams/{teamId}/statistics
```

The backend would therefore act as the boundary between the database and the presentation layer.

It could also perform calculations that are more appropriate on the server side, such as aggregations, rankings, averages, or comparative statistics.

### Frontend

The web interface could be implemented using:

`HTML · CSS · JavaScript · Tailwind CSS`

The frontend would consume the REST API and transform the data into interactive visualizations.

Possible views include:

```text
Dashboard
├── Season overview
├── Race explorer
├── Driver comparison
├── Team comparison
└── Race analysis
```

Charts could show, for example, lap-time evolution, race position changes, tyre stints, or driver comparisons.

---

## Docker

The complete system could be reproducible through Docker Compose.

```text
docker-compose
│
├── frontend
├── backend
└── postgres
```

The goal is that another developer can clone the repository and start the complete application with a minimal setup.

The data ingestion pipeline could either run as a separate container or as an explicit initialization/update process.

---

## Publication

The project should be published as a GitHub repository containing:

```text
f1-data-platform/
├── backend/
├── frontend/
├── data-pipeline/
├── database/
├── docker-compose.yml
├── README.md
└── LICENSE
```

The README should explain:

1. what the platform does;
2. why it exists;
3. the architecture;
4. the data pipeline;
5. the database model;
6. the API;
7. how to run the project locally;
8. screenshots of the dashboard;
9. example API requests;
10. technical decisions and trade-offs.

The repository should also contain an architecture diagram and a small sample dataset so that the project remains reproducible without requiring access to the original external data source.

---

## Portfolio Presentation

On the portfolio website, the project should be presented as a **data engineering / backend project**, rather than simply as an F1-themed website.

A project card could emphasize:

> **F1 Data Platform**
> End-to-end data pipeline and analytics platform for Formula 1 racing data.

The technology list could be:

`Python · PostgreSQL · Java · Spring Boot · REST · JavaScript · Tailwind CSS · Docker`

The portfolio page could then contain:

```text
Problem
    ↓
Architecture
    ↓
Data Pipeline
    ↓
Database
    ↓
API
    ↓
Dashboard
```

This makes the project useful as evidence of backend, data processing, database, API, web, and containerization skills, while the Formula 1 domain gives it a distinctive identity.

---

## What the Project Demonstrates

The project should ultimately demonstrate the ability to:

* work with external datasets;
* design a relational data model;
* build reproducible data pipelines;
* process and transform structured data with Python;
* design REST APIs;
* build a backend with Spring Boot;
* work with PostgreSQL;
* create a web interface consuming APIs;
* visualize structured data;
* containerize a multi-component application;
* document an end-to-end software system.

The central idea is therefore not "I built an F1 website", but:

> **I designed and implemented an end-to-end system that transforms raw data into an accessible analytical product.**

---

## Data Source & Acknowledgements

The historical Formula 1 CSV datasets used in this project are sourced from Kaggle:

* **Dataset:** [Formula 1 World Championship (1950 - 2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020)
* **Author / Maintainer:** [Rohan Rao](https://www.kaggle.com/rohanrao)
* **Original Data Origin:** [Ergast Developer API](https://ergast.com/mrd/)