import csv
import os
import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).resolve().parent / "raw"
BATCH_SIZE = 2000


def get_value(row, column):
    value = row.get(column)
    if value is None or value == "" or value == r"\N":
        return None
    return value


def get_int(row, column):
    value = get_value(row, column)
    return int(value) if value is not None else None


def get_float(row, column):
    value = get_value(row, column)
    return float(value) if value is not None else None


def get_date(value):
    return date.fromisoformat(value) if value else None


def get_time(value):
    if not value:
        return None
    return time.fromisoformat(value.removesuffix("Z"))


def get_duration_ms(value):
    if not value:
        return None
    if ":" in value:
        minutes, seconds = value.split(":", maxsplit=1)
        return int(Decimal(minutes) * 60_000 + Decimal(seconds) * 1_000)
    return int(Decimal(value) * 1_000)


def csv_rows(filename):
    path = RAW / filename
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"Il CSV {path} non contiene intestazioni")
        yield from reader


def insert_rows(cursor, table, columns, rows, conflict="DO NOTHING"):
    column_list = ", ".join(columns)
    statement = (
        f"INSERT INTO {table} ({column_list}) VALUES %s "
        f"ON CONFLICT {conflict}"
    )
    batch = []
    inserted = 0
    for row in rows:
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            execute_values(cursor, statement, batch, page_size=BATCH_SIZE)
            inserted += len(batch)
            batch.clear()
    if batch:
        execute_values(cursor, statement, batch, page_size=BATCH_SIZE)
        inserted += len(batch)
    return inserted


def load_sessions(cursor):
    session_fields = (
        ("FP1", "fp1_date", "fp1_time"),
        ("FP2", "fp2_date", "fp2_time"),
        ("FP3", "fp3_date", "fp3_time"),
        ("Q", "quali_date", "quali_time"),
        ("SPRINT", "sprint_date", "sprint_time"),
        ("RACE", "date", "time"),
    )

    def rows():
        for race in csv_rows("races.csv"):
            race_id = get_int(race, "raceId")
            for session_type, date_column, time_column in session_fields:
                session_date = get_date(get_value(race, date_column))
                session_time = get_time(get_value(race, time_column))
                if session_date is not None or session_time is not None:
                    yield (race_id, session_type, session_date, session_time)

    return insert_rows(
        cursor,
        "sessions",
        ("race_id", "session_type", "session_date", "session_time"),
        rows(),
        conflict="(race_id, session_type) DO NOTHING",
    )


def load_all(cursor):
    counts = {}

    counts["seasons"] = insert_rows(
        cursor,
        "seasons",
        ("season_year",),
        ((get_int(row, "year"),) for row in csv_rows("seasons.csv")),
    )
    counts["circuits"] = insert_rows(
        cursor,
        "circuits",
        ("circuit_id", "circuit_ref", "name", "location", "country", "lat", "lng", "altitude_m"),
        (
            (
                get_int(row, "circuitId"),
                get_value(row, "circuitRef"),
                get_value(row, "name"),
                get_value(row, "location"),
                get_value(row, "country"),
                get_float(row, "lat"),
                get_float(row, "lng"),
                get_int(row, "alt"),
            )
            for row in csv_rows("circuits.csv")
        ),
    )
    counts["drivers"] = insert_rows(
        cursor,
        "drivers",
        ("driver_id", "driver_ref", "car_number", "code", "forename", "surname", "dob", "nationality"),
        (
            (
                get_int(row, "driverId"),
                get_value(row, "driverRef"),
                get_int(row, "number"),
                get_value(row, "code"),
                get_value(row, "forename"),
                get_value(row, "surname"),
                get_date(get_value(row, "dob")),
                get_value(row, "nationality"),
            )
            for row in csv_rows("drivers.csv")
        ),
    )
    counts["constructors"] = insert_rows(
        cursor,
        "constructors",
        ("constructor_id", "constructor_ref", "name", "nationality"),
        (
            (
                get_int(row, "constructorId"),
                get_value(row, "constructorRef"),
                get_value(row, "name"),
                get_value(row, "nationality"),
            )
            for row in csv_rows("constructors.csv")
        ),
    )
    counts["statuses"] = insert_rows(
        cursor,
        "statuses",
        ("status_id", "status"),
        ((get_int(row, "statusId"), get_value(row, "status")) for row in csv_rows("status.csv")),
    )
    counts["races"] = insert_rows(
        cursor,
        "races",
        ("race_id", "season_year", "round", "circuit_id", "name"),
        (
            (
                get_int(row, "raceId"),
                get_int(row, "year"),
                get_int(row, "round"),
                get_int(row, "circuitId"),
                get_value(row, "name"),
            )
            for row in csv_rows("races.csv")
        ),
    )
    counts["sessions"] = load_sessions(cursor)

    counts["results"] = insert_rows(
        cursor,
        "results",
        (
            "result_id", "race_id", "driver_id", "constructor_id", "car_number", "grid",
            "position", "position_text", "position_order", "points", "laps_completed",
            "race_time_ms", "fastest_lap_number", "fastest_lap_time_ms", "fastest_lap_rank",
            "fastest_lap_speed_kmh", "status_id",
        ),
        (
            (
                get_int(row, "resultId"), get_int(row, "raceId"), get_int(row, "driverId"),
                get_int(row, "constructorId"), get_int(row, "number"), get_int(row, "grid"),
                get_int(row, "position"), get_value(row, "positionText"),
                get_int(row, "positionOrder"), get_value(row, "points"), get_int(row, "laps"),
                get_int(row, "milliseconds"), get_int(row, "fastestLap"),
                get_duration_ms(get_value(row, "fastestLapTime")), get_int(row, "rank"),
                get_float(row, "fastestLapSpeed"), get_int(row, "statusId"),
            )
            for row in csv_rows("results.csv")
        ),
    )
    counts["qualifying"] = insert_rows(
        cursor,
        "qualifying",
        ("qualify_id", "race_id", "driver_id", "constructor_id", "car_number", "quali_position", "q1_time_ms", "q2_time_ms", "q3_time_ms"),
        (
            (
                get_int(row, "qualifyId"), get_int(row, "raceId"), get_int(row, "driverId"),
                get_int(row, "constructorId"), get_int(row, "number"), get_int(row, "position"),
                get_duration_ms(get_value(row, "q1")), get_duration_ms(get_value(row, "q2")),
                get_duration_ms(get_value(row, "q3")),
            )
            for row in csv_rows("qualifying.csv")
        ),
    )
    counts["sprint_results"] = insert_rows(
        cursor,
        "sprint_results",
        (
            "result_id", "race_id", "driver_id", "constructor_id", "car_number", "grid",
            "position", "position_text", "position_order", "points", "laps_completed",
            "race_time_ms", "fastest_lap_number", "fastest_lap_time_ms", "status_id",
        ),
        (
            (
                get_int(row, "resultId"), get_int(row, "raceId"), get_int(row, "driverId"),
                get_int(row, "constructorId"), get_int(row, "number"), get_int(row, "grid"),
                get_int(row, "position"), get_value(row, "positionText"),
                get_int(row, "positionOrder"), get_value(row, "points"), get_int(row, "laps"),
                get_int(row, "milliseconds"), get_int(row, "fastestLap"),
                get_duration_ms(get_value(row, "fastestLapTime")), get_int(row, "statusId"),
            )
            for row in csv_rows("sprint_results.csv")
        ),
    )
    counts["constructor_results"] = insert_rows(
        cursor,
        "constructor_results",
        ("constructor_result_id", "race_id", "constructor_id", "points", "status"),
        (
            (
                get_int(row, "constructorResultsId"), get_int(row, "raceId"),
                get_int(row, "constructorId"), get_value(row, "points"),
                get_value(row, "status"),
            )
            for row in csv_rows("constructor_results.csv")
        ),
    )
    counts["driver_standings"] = insert_rows(
        cursor,
        "driver_standings",
        ("standings_id", "race_id", "driver_id", "points", "position", "position_text", "wins"),
        (
            (
                get_int(row, "driverStandingsId"), get_int(row, "raceId"),
                get_int(row, "driverId"), get_value(row, "points"),
                get_int(row, "position"), get_value(row, "positionText"), get_int(row, "wins"),
            )
            for row in csv_rows("driver_standings.csv")
        ),
    )
    counts["constructor_standings"] = insert_rows(
        cursor,
        "constructor_standings",
        ("standings_id", "race_id", "constructor_id", "points", "position", "position_text", "wins"),
        (
            (
                get_int(row, "constructorStandingsId"), get_int(row, "raceId"),
                get_int(row, "constructorId"), get_value(row, "points"),
                get_int(row, "position"), get_value(row, "positionText"), get_int(row, "wins"),
            )
            for row in csv_rows("constructor_standings.csv")
        ),
    )
    counts["laps"] = insert_rows(
        cursor,
        "laps",
        ("race_id", "driver_id", "lap", "position", "lap_time_ms"),
        (
            (
                get_int(row, "raceId"), get_int(row, "driverId"), get_int(row, "lap"),
                get_int(row, "position"),
                get_int(row, "milliseconds") or get_duration_ms(get_value(row, "time")),
            )
            for row in csv_rows("lap_times.csv")
        ),
    )
    counts["pit_stops"] = insert_rows(
        cursor,
        "pit_stops",
        ("race_id", "driver_id", "stop", "lap", "time_of_day", "duration_ms"),
        (
            (
                get_int(row, "raceId"), get_int(row, "driverId"), get_int(row, "stop"),
                get_int(row, "lap"), get_time(get_value(row, "time")),
                get_int(row, "milliseconds") or get_duration_ms(get_value(row, "duration")),
            )
            for row in csv_rows("pit_stops.csv")
        ),
    )
    return counts


def main():
    filenames = (
        "circuits.csv", "constructor_results.csv", "constructor_standings.csv",
        "constructors.csv", "driver_standings.csv", "drivers.csv", "lap_times.csv",
        "pit_stops.csv", "qualifying.csv", "races.csv", "results.csv", "seasons.csv",
        "sprint_results.csv", "status.csv",
    )
    missing = [name for name in filenames if not (RAW / name).is_file()]
    if missing:
        print(f"CSV mancanti in {RAW}: {', '.join(missing)}", file=sys.stderr)
        return 1

    load_dotenv(ROOT / ".env")
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    unset = [name for name in required if os.getenv(name) is None]
    if unset:
        print(f"Variabili mancanti nel file .env: {', '.join(unset)}", file=sys.stderr)
        return 1

    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
        try:
            with connection:
                with connection.cursor() as cursor:
                    counts = load_all(cursor)
        finally:
            connection.close()
    except Exception as error:
        print(f"Import annullato: {error}", file=sys.stderr)
        return 1

    print("Import completato (righe lette; i duplicati esistenti sono ignorati):")
    for table, count in counts.items():
        print(f"  {table}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())