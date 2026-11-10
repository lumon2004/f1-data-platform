-- F1 Data Platform - V2: Gran Premi (races) e sessioni del weekend (sessions).
-- Le motivazioni di ogni scelta sono in docs/modello-dati.md.

CREATE TABLE races (
    id            integer NOT NULL,
    season_year   integer NOT NULL,
    round         integer NOT NULL,
    circuit_id    integer NOT NULL,
    name          text    NOT NULL,
    wikipedia_url text,
    CONSTRAINT pk_races PRIMARY KEY (id),
    CONSTRAINT uq_races_season_round UNIQUE (season_year, round),
    CONSTRAINT fk_races_season FOREIGN KEY (season_year) REFERENCES seasons (year),
    CONSTRAINT fk_races_circuit FOREIGN KEY (circuit_id) REFERENCES circuits (id),
    CONSTRAINT ck_races_round CHECK (round > 0),
    CONSTRAINT ck_races_name CHECK (name <> '')
);

-- Gare disputate su un circuito e sostegno alla chiave esterna verso circuits.
CREATE INDEX idx_races_circuit ON races (circuit_id);

COMMENT ON TABLE races IS 'Gran Premi: un evento (weekend) per riga. Chiave naturale: stagione + round. Date e orari stanno in sessions.';


CREATE TABLE sessions (
    race_id        integer NOT NULL,
    session_type   text    NOT NULL,
    session_date   date,
    start_time_utc time,
    CONSTRAINT pk_sessions PRIMARY KEY (race_id, session_type),
    CONSTRAINT fk_sessions_race FOREIGN KEY (race_id) REFERENCES races (id),
    CONSTRAINT ck_sessions_type
        CHECK (session_type IN ('fp1', 'fp2', 'fp3', 'qualifying', 'sprint', 'race')),
    -- La sessione di gara porta la data del Gran Premio: e obbligatoria.
    CONSTRAINT ck_sessions_race_has_date
        CHECK (session_type <> 'race' OR session_date IS NOT NULL),
    -- Un orario senza data non ha significato.
    CONSTRAINT ck_sessions_time_needs_date
        CHECK (start_time_utc IS NULL OR session_date IS NOT NULL)
);

COMMENT ON TABLE sessions IS 'Sessioni di un weekend di gara. La chiave e la chiave naturale: gara + tipo di sessione.';
COMMENT ON COLUMN sessions.session_date IS 'Data della sessione. Obbligatoria per la gara; NULL quando la fonte non la riporta (es. qualifiche prima del 2021).';
COMMENT ON COLUMN sessions.start_time_utc IS 'Orario di inizio in UTC. NULL quando la fonte non lo riporta (gran parte delle stagioni storiche).';
