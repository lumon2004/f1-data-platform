-- F1 Data Platform - V3: classifiche di sessione.
--   results            classifica di gara e di sprint (stessa struttura, distinte da session_type)
--   qualifying_results classifica di qualifica (tempi Q1/Q2/Q3)
-- Le motivazioni di ogni scelta sono in docs/modello-dati.md.

CREATE TABLE results (
    id                    integer GENERATED ALWAYS AS IDENTITY,
    race_id               integer NOT NULL,
    session_type          text    NOT NULL,
    source_id             integer NOT NULL,
    driver_id             integer NOT NULL,
    constructor_id        integer NOT NULL,
    status_id             integer NOT NULL,
    car_number            integer,
    grid_position         integer,
    position              integer,
    position_order        integer NOT NULL,
    outcome               text    NOT NULL,
    points                numeric(6, 2) NOT NULL,
    laps_completed        integer NOT NULL,
    time_ms               integer,
    fastest_lap_number    integer,
    fastest_lap_rank      integer,
    fastest_lap_time_ms   integer,
    fastest_lap_speed_kph numeric(7, 3),
    CONSTRAINT pk_results PRIMARY KEY (id),
    -- Chiave di caricamento (ON CONFLICT): identificativo della riga nella fonte,
    -- qualificato dal tipo di sessione perche gare e sprint hanno numerazioni separate.
    CONSTRAINT uq_results_source UNIQUE (session_type, source_id),
    CONSTRAINT fk_results_session FOREIGN KEY (race_id, session_type)
        REFERENCES sessions (race_id, session_type),
    CONSTRAINT fk_results_driver FOREIGN KEY (driver_id) REFERENCES drivers (id),
    CONSTRAINT fk_results_constructor FOREIGN KEY (constructor_id) REFERENCES constructors (id),
    CONSTRAINT fk_results_status FOREIGN KEY (status_id) REFERENCES statuses (id),
    CONSTRAINT ck_results_session_type CHECK (session_type IN ('race', 'sprint')),
    CONSTRAINT ck_results_outcome CHECK (outcome IN (
        'classified', 'retired', 'disqualified', 'excluded',
        'withdrawn', 'failed_to_qualify', 'not_classified')),
    -- La posizione finale esiste se e solo se il pilota e classificato.
    CONSTRAINT ck_results_outcome_position CHECK ((outcome = 'classified') = (position IS NOT NULL)),
    CONSTRAINT ck_results_car_number CHECK (car_number >= 0),
    CONSTRAINT ck_results_grid_position CHECK (grid_position > 0),
    CONSTRAINT ck_results_position CHECK (position > 0),
    CONSTRAINT ck_results_position_order CHECK (position_order > 0),
    CONSTRAINT ck_results_points CHECK (points >= 0),
    CONSTRAINT ck_results_laps_completed CHECK (laps_completed >= 0),
    CONSTRAINT ck_results_time_ms CHECK (time_ms > 0),
    CONSTRAINT ck_results_fastest_lap_number CHECK (fastest_lap_number > 0),
    CONSTRAINT ck_results_fastest_lap_rank CHECK (fastest_lap_rank > 0),
    CONSTRAINT ck_results_fastest_lap_time_ms CHECK (fastest_lap_time_ms > 0),
    CONSTRAINT ck_results_fastest_lap_speed_kph CHECK (fastest_lap_speed_kph > 0)
);

-- Classifica di una sessione, gia nell'ordine di arrivo: GET /api/races/{raceId}/results.
CREATE INDEX idx_results_session_order ON results (race_id, session_type, position_order);
-- Statistiche di un pilota (gare, vittorie, podi, punti), anche per stagione tramite race_id.
CREATE INDEX idx_results_driver ON results (driver_id, session_type, race_id);
-- Statistiche di una scuderia.
CREATE INDEX idx_results_constructor ON results (constructor_id, session_type, race_id);

COMMENT ON TABLE results IS 'Classifica di una sessione che assegna punti (gara o sprint): una riga per partecipazione pilota-vettura.';
COMMENT ON COLUMN results.source_id IS 'Identificativo della riga nella fonte (resultId), univoco solo dentro lo stesso session_type.';
COMMENT ON COLUMN results.grid_position IS 'Posizione in griglia. NULL = nessuna casella (partenza dalla pit lane o non partito).';
COMMENT ON COLUMN results.position IS 'Posizione finale ufficiale. NULL se il pilota non e classificato (vedi outcome).';
COMMENT ON COLUMN results.position_order IS 'Ordine completo della classifica, valorizzato anche per i non classificati: serve per ordinare.';
COMMENT ON COLUMN results.time_ms IS 'Tempo totale di gara in millisecondi. Presente solo per chi termina a pieni giri.';
COMMENT ON COLUMN results.fastest_lap_rank IS 'Posizione del giro veloce del pilota tra i giri veloci di tutti (1 = giro piu veloce della gara).';


CREATE TABLE qualifying_results (
    race_id        integer NOT NULL,
    session_type   text    NOT NULL,
    driver_id      integer NOT NULL,
    constructor_id integer NOT NULL,
    car_number     integer,
    position       integer NOT NULL,
    q1_ms          integer,
    q2_ms          integer,
    q3_ms          integer,
    CONSTRAINT pk_qualifying_results PRIMARY KEY (race_id, session_type, driver_id),
    CONSTRAINT fk_qualifying_results_session FOREIGN KEY (race_id, session_type)
        REFERENCES sessions (race_id, session_type),
    CONSTRAINT fk_qualifying_results_driver FOREIGN KEY (driver_id) REFERENCES drivers (id),
    CONSTRAINT fk_qualifying_results_constructor FOREIGN KEY (constructor_id) REFERENCES constructors (id),
    CONSTRAINT ck_qualifying_results_session_type CHECK (session_type = 'qualifying'),
    CONSTRAINT ck_qualifying_results_car_number CHECK (car_number >= 0),
    CONSTRAINT ck_qualifying_results_position CHECK (position > 0),
    CONSTRAINT ck_qualifying_results_q1_ms CHECK (q1_ms > 0),
    CONSTRAINT ck_qualifying_results_q2_ms CHECK (q2_ms > 0),
    CONSTRAINT ck_qualifying_results_q3_ms CHECK (q3_ms > 0)
);

COMMENT ON TABLE qualifying_results IS 'Classifica di qualifica: una riga per pilota, con i migliori tempi di Q1, Q2 e Q3 in millisecondi.';
