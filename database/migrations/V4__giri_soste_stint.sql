-- F1 Data Platform - V4: dati giro per giro (laps), soste ai box (pit_stops) e stint (stints).
-- Le tre tabelle usano come chiave primaria la propria chiave naturale, che inizia con
-- (race_id, session_type, driver_id): la stessa chiave serve le letture "pilota in una gara".
-- Le motivazioni di ogni scelta sono in docs/modello-dati.md.

CREATE TABLE laps (
    race_id      integer NOT NULL,
    session_type text    NOT NULL,
    driver_id    integer NOT NULL,
    lap_number   integer NOT NULL,
    position     integer,
    time_ms      integer NOT NULL,
    CONSTRAINT pk_laps PRIMARY KEY (race_id, session_type, driver_id, lap_number),
    CONSTRAINT fk_laps_session FOREIGN KEY (race_id, session_type)
        REFERENCES sessions (race_id, session_type),
    CONSTRAINT fk_laps_driver FOREIGN KEY (driver_id) REFERENCES drivers (id),
    CONSTRAINT ck_laps_lap_number CHECK (lap_number > 0),
    CONSTRAINT ck_laps_position CHECK (position > 0),
    CONSTRAINT ck_laps_time_ms CHECK (time_ms > 0)
);

COMMENT ON TABLE laps IS 'Un giro cronometrato di un pilota in una sessione. La fonte li fornisce solo per le gare, dal 1996.';
COMMENT ON COLUMN laps.position IS 'Posizione in pista al termine del giro.';
COMMENT ON COLUMN laps.time_ms IS 'Tempo sul giro in millisecondi.';


CREATE TABLE pit_stops (
    race_id      integer NOT NULL,
    session_type text    NOT NULL,
    driver_id    integer NOT NULL,
    stop_number  integer NOT NULL,
    lap_number   integer NOT NULL,
    time_of_day  time,
    duration_ms  integer,
    CONSTRAINT pk_pit_stops PRIMARY KEY (race_id, session_type, driver_id, stop_number),
    CONSTRAINT fk_pit_stops_session FOREIGN KEY (race_id, session_type)
        REFERENCES sessions (race_id, session_type),
    CONSTRAINT fk_pit_stops_driver FOREIGN KEY (driver_id) REFERENCES drivers (id),
    CONSTRAINT ck_pit_stops_session_type CHECK (session_type IN ('race', 'sprint')),
    CONSTRAINT ck_pit_stops_stop_number CHECK (stop_number > 0),
    CONSTRAINT ck_pit_stops_lap_number CHECK (lap_number > 0),
    CONSTRAINT ck_pit_stops_duration_ms CHECK (duration_ms > 0)
);

COMMENT ON TABLE pit_stops IS 'Una sosta ai box di un pilota in una sessione. La fonte le fornisce solo per le gare, dal 2011.';
COMMENT ON COLUMN pit_stops.lap_number IS 'Giro al termine del quale il pilota entra ai box.';
COMMENT ON COLUMN pit_stops.time_of_day IS 'Ora locale del circuito al momento della sosta.';
COMMENT ON COLUMN pit_stops.duration_ms IS 'Durata della sosta (tempo in pit lane) in millisecondi.';


CREATE TABLE stints (
    race_id      integer NOT NULL,
    session_type text    NOT NULL,
    driver_id    integer NOT NULL,
    stint_number integer NOT NULL,
    start_lap    integer NOT NULL,
    end_lap      integer NOT NULL,
    compound     text,
    CONSTRAINT pk_stints PRIMARY KEY (race_id, session_type, driver_id, stint_number),
    -- Due stint dello stesso pilota non possono iniziare allo stesso giro.
    CONSTRAINT uq_stints_start_lap UNIQUE (race_id, session_type, driver_id, start_lap),
    CONSTRAINT fk_stints_session FOREIGN KEY (race_id, session_type)
        REFERENCES sessions (race_id, session_type),
    CONSTRAINT fk_stints_driver FOREIGN KEY (driver_id) REFERENCES drivers (id),
    CONSTRAINT ck_stints_session_type CHECK (session_type IN ('race', 'sprint')),
    CONSTRAINT ck_stints_stint_number CHECK (stint_number > 0),
    CONSTRAINT ck_stints_start_lap CHECK (start_lap > 0),
    CONSTRAINT ck_stints_lap_range CHECK (end_lap >= start_lap),
    CONSTRAINT ck_stints_compound CHECK (compound <> '' AND compound = lower(compound))
);

COMMENT ON TABLE stints IS 'Tratto di gara di un pilota tra due soste. Tabella derivata dalla pipeline a partire da pit_stops e results.';
COMMENT ON COLUMN stints.start_lap IS 'Primo giro dello stint (1 oppure giro della sosta precedente + 1).';
COMMENT ON COLUMN stints.end_lap IS 'Ultimo giro dello stint (giro della sosta successiva oppure ultimo giro completato).';
COMMENT ON COLUMN stints.compound IS 'Mescola. Sempre NULL con la fonte attuale, che non contiene le mescole.';
