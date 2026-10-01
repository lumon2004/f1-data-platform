-- ============================================================
-- F1 Data Platform — Initial schema
-- Source: Kaggle dataset "Formula 1 World Championship (1950-2024)"
--         (export of the deprecated Ergast API)
--
-- Design decisions compared to source CSVs (see analysis):
--  - sparse date/time columns from races.csv -> `sessions` table
--  - redundant text/millisecond pairs -> keep only milliseconds
--  - `url` (Wikipedia) columns -> omitted
--  - number/points with NaN -> proper nullable types (SMALLINT, NUMERIC)
--  - Ergast surrogate IDs preserved as PKs for source traceability
-- ============================================================

-- ---------- Reference tables ----------

CREATE TABLE seasons (
    season_year     SMALLINT PRIMARY KEY
);

CREATE TABLE circuits (
    circuit_id      INTEGER PRIMARY KEY,
    circuit_ref     VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(100),
    country         VARCHAR(100),
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    altitude_m      INTEGER
);

CREATE TABLE drivers (
    driver_id       INTEGER PRIMARY KEY,
    driver_ref      VARCHAR(50) NOT NULL UNIQUE,
    car_number      SMALLINT,              -- nullable: not all drivers had a permanent racing number historically
    code            CHAR(3),               -- nullable: three-letter code introduced only in 2014
    forename        VARCHAR(50) NOT NULL,
    surname         VARCHAR(50) NOT NULL,
    dob             DATE,
    nationality     VARCHAR(50)
);

CREATE TABLE constructors (
    constructor_id      INTEGER PRIMARY KEY,
    constructor_ref     VARCHAR(50) NOT NULL UNIQUE,
    name                VARCHAR(100) NOT NULL,
    nationality         VARCHAR(50)
);

CREATE TABLE statuses (
    status_id       INTEGER PRIMARY KEY,
    status          VARCHAR(100) NOT NULL
);

-- ---------- Races and sessions ----------

CREATE TABLE races (
    race_id         INTEGER PRIMARY KEY,
    season_year     SMALLINT NOT NULL REFERENCES seasons(season_year),
    round           SMALLINT NOT NULL,
    circuit_id      INTEGER NOT NULL REFERENCES circuits(circuit_id),
    name            VARCHAR(100) NOT NULL,
    UNIQUE (season_year, round)
);

-- Normalizes the 10 sparse fp1/fp2/fp3/quali/sprint date+time columns from races.csv:
-- one row per session actually held, no empty columns for sessions
-- that did not exist during that weekend (e.g. sprints before 2021).
CREATE TABLE sessions (
    session_id      SERIAL PRIMARY KEY,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    session_type    VARCHAR(10) NOT NULL
                        CHECK (session_type IN ('FP1','FP2','FP3','Q','SPRINT','RACE')),
    session_date    DATE,
    session_time    TIME,               -- nullable: not always recorded historically
    UNIQUE (race_id, session_type)
);

-- ---------- Results ----------

CREATE TABLE results (
    result_id           INTEGER PRIMARY KEY,
    race_id             INTEGER NOT NULL REFERENCES races(race_id),
    driver_id           INTEGER NOT NULL REFERENCES drivers(driver_id),
    constructor_id      INTEGER NOT NULL REFERENCES constructors(constructor_id),
    car_number          SMALLINT,                  -- nullable: 6 rows without a number in source
    grid                SMALLINT NOT NULL,
    position            SMALLINT,                  -- NULL if not classified (retirement/disqualification)
    position_text       VARCHAR(4) NOT NULL,        -- 'R','D',... when position is NULL
    position_order      SMALLINT NOT NULL,          -- stable ordering key, never NULL
    points              NUMERIC(6,2) NOT NULL DEFAULT 0,
    laps_completed      SMALLINT NOT NULL,
    race_time_ms        INTEGER,                   -- NULL if not classified on the leader's lap
    fastest_lap_number  SMALLINT,
    fastest_lap_time_ms INTEGER,                   -- parsed in pipeline from textual fastestLapTime
    fastest_lap_rank    SMALLINT,
    fastest_lap_speed_kmh REAL,
    status_id           INTEGER NOT NULL REFERENCES statuses(status_id)
);

CREATE TABLE qualifying (
    qualify_id      INTEGER PRIMARY KEY,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    driver_id       INTEGER NOT NULL REFERENCES drivers(driver_id),
    constructor_id  INTEGER NOT NULL REFERENCES constructors(constructor_id),
    car_number      SMALLINT NOT NULL,
    quali_position  SMALLINT NOT NULL,
    q1_time_ms      INTEGER,            -- parsed in pipeline from textual q1/q2/q3
    q2_time_ms      INTEGER,
    q3_time_ms      INTEGER
);

CREATE TABLE sprint_results (
    result_id           INTEGER PRIMARY KEY,
    race_id             INTEGER NOT NULL REFERENCES races(race_id),
    driver_id           INTEGER NOT NULL REFERENCES drivers(driver_id),
    constructor_id      INTEGER NOT NULL REFERENCES constructors(constructor_id),
    car_number          SMALLINT NOT NULL,
    grid                SMALLINT NOT NULL,
    position            SMALLINT,
    position_text       VARCHAR(4) NOT NULL,
    position_order      SMALLINT NOT NULL,
    points              NUMERIC(6,2) NOT NULL DEFAULT 0,
    laps_completed      SMALLINT NOT NULL,
    race_time_ms        INTEGER,
    fastest_lap_number  SMALLINT,
    fastest_lap_time_ms INTEGER,
    status_id           INTEGER NOT NULL REFERENCES statuses(status_id)
);

CREATE TABLE constructor_results (
    constructor_result_id  INTEGER PRIMARY KEY,
    race_id                 INTEGER NOT NULL REFERENCES races(race_id),
    constructor_id          INTEGER NOT NULL REFERENCES constructors(constructor_id),
    points                  NUMERIC(6,2) NOT NULL DEFAULT 0,
    status                  VARCHAR(50)      -- almost always NULL; used for team-level disqualifications
);

-- ---------- Cumulative standings ----------

CREATE TABLE driver_standings (
    standings_id    INTEGER PRIMARY KEY,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    driver_id       INTEGER NOT NULL REFERENCES drivers(driver_id),
    points          NUMERIC(6,2) NOT NULL,
    position        SMALLINT NOT NULL,
    position_text   VARCHAR(4) NOT NULL,
    wins            SMALLINT NOT NULL,
    UNIQUE (race_id, driver_id)
);

CREATE TABLE constructor_standings (
    standings_id    INTEGER PRIMARY KEY,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    constructor_id  INTEGER NOT NULL REFERENCES constructors(constructor_id),
    points          NUMERIC(6,2) NOT NULL,
    position        SMALLINT NOT NULL,
    position_text   VARCHAR(4) NOT NULL,
    wins            SMALLINT NOT NULL,
    UNIQUE (race_id, constructor_id)
);

-- ---------- Granular race data ----------

CREATE TABLE laps (
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    driver_id       INTEGER NOT NULL REFERENCES drivers(driver_id),
    lap             SMALLINT NOT NULL,
    position         SMALLINT NOT NULL,     -- track position at lap end
    lap_time_ms      INTEGER NOT NULL,
    PRIMARY KEY (race_id, driver_id, lap)
);

CREATE TABLE pit_stops (
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    driver_id       INTEGER NOT NULL REFERENCES drivers(driver_id),
    stop            SMALLINT NOT NULL,
    lap             SMALLINT NOT NULL,
    time_of_day     TIME NOT NULL,
    duration_ms     INTEGER NOT NULL,
    PRIMARY KEY (race_id, driver_id, stop)
);

-- ---------- Indexes for API query patterns (/api/races/{id}/laps/{driverId}, etc.) ----------

CREATE INDEX idx_results_race ON results(race_id);
CREATE INDEX idx_results_driver ON results(driver_id);
CREATE INDEX idx_laps_race_driver ON laps(race_id, driver_id);
CREATE INDEX idx_standings_race ON driver_standings(race_id);
CREATE INDEX idx_constructor_standings_race ON constructor_standings(race_id);
