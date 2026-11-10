-- F1 Data Platform - V1: anagrafiche (stagioni, circuiti, piloti, scuderie, stati di arrivo).
-- Le motivazioni di ogni scelta sono in docs/modello-dati.md.
--
-- Convenzione sulle chiavi: la colonna "id" delle anagrafiche non e generata dal database.
-- La valorizza la pipeline con l'identificativo stabile ereditato dalla fonte; accanto a essa
-- ogni tabella dichiara la propria chiave naturale con un vincolo UNIQUE.

CREATE TABLE seasons (
    year          integer NOT NULL,
    wikipedia_url text,
    CONSTRAINT pk_seasons PRIMARY KEY (year),
    CONSTRAINT ck_seasons_year CHECK (year BETWEEN 1950 AND 2100)
);

COMMENT ON TABLE seasons IS 'Stagioni del campionato. La chiave e la chiave naturale: l''anno.';


CREATE TABLE circuits (
    id            integer NOT NULL,
    ref           text    NOT NULL,
    name          text    NOT NULL,
    locality      text,
    country       text    NOT NULL,
    latitude      numeric(9, 6),
    longitude     numeric(9, 6),
    altitude_m    integer,
    wikipedia_url text,
    CONSTRAINT pk_circuits PRIMARY KEY (id),
    CONSTRAINT uq_circuits_ref UNIQUE (ref),
    CONSTRAINT ck_circuits_ref CHECK (ref <> ''),
    CONSTRAINT ck_circuits_name CHECK (name <> ''),
    CONSTRAINT ck_circuits_country CHECK (country <> ''),
    CONSTRAINT ck_circuits_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_circuits_longitude CHECK (longitude BETWEEN -180 AND 180)
);

COMMENT ON TABLE circuits IS 'Circuiti. Chiave naturale: ref (slug testuale della fonte).';
COMMENT ON COLUMN circuits.altitude_m IS 'Altitudine in metri sul livello del mare; puo essere negativa.';


CREATE TABLE drivers (
    id               integer NOT NULL,
    ref              text    NOT NULL,
    given_name       text    NOT NULL,
    family_name      text    NOT NULL,
    code             text,
    permanent_number integer,
    date_of_birth    date,
    nationality      text,
    wikipedia_url    text,
    CONSTRAINT pk_drivers PRIMARY KEY (id),
    CONSTRAINT uq_drivers_ref UNIQUE (ref),
    CONSTRAINT ck_drivers_ref CHECK (ref <> ''),
    CONSTRAINT ck_drivers_given_name CHECK (given_name <> ''),
    CONSTRAINT ck_drivers_family_name CHECK (family_name <> ''),
    CONSTRAINT ck_drivers_code CHECK (char_length(code) = 3 AND code = upper(code)),
    CONSTRAINT ck_drivers_permanent_number CHECK (permanent_number BETWEEN 0 AND 99)
);

COMMENT ON TABLE drivers IS 'Piloti. Chiave naturale: ref (slug testuale della fonte).';
COMMENT ON COLUMN drivers.code IS 'Sigla di tre lettere (es. VER). Assente per molti piloti storici e non univoca tra piloti diversi.';
COMMENT ON COLUMN drivers.permanent_number IS 'Numero di gara permanente scelto dal pilota (dal 2014). Il numero usato in una singola gara sta in results.car_number.';


CREATE TABLE constructors (
    id            integer NOT NULL,
    ref           text    NOT NULL,
    name          text    NOT NULL,
    nationality   text,
    wikipedia_url text,
    CONSTRAINT pk_constructors PRIMARY KEY (id),
    CONSTRAINT uq_constructors_ref UNIQUE (ref),
    CONSTRAINT ck_constructors_ref CHECK (ref <> ''),
    CONSTRAINT ck_constructors_name CHECK (name <> '')
);

COMMENT ON TABLE constructors IS 'Scuderie (costruttori). Chiave naturale: ref (slug testuale della fonte).';


CREATE TABLE statuses (
    id   integer NOT NULL,
    name text    NOT NULL,
    CONSTRAINT pk_statuses PRIMARY KEY (id),
    CONSTRAINT uq_statuses_name UNIQUE (name),
    CONSTRAINT ck_statuses_name CHECK (name <> '')
);

COMMENT ON TABLE statuses IS 'Stati di arrivo di un risultato (Finished, +1 Lap, Engine, Collision, ...). Chiave naturale: name.';
