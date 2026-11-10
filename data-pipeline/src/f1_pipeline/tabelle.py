"""Tabelle dello schema viste dalla pipeline: colonne, tipi Arrow, chiavi.

È l'unico punto in cui la pipeline nomina tabelle e colonne del database
(definite dalle migrazioni in database/migrations/ e descritte in
docs/modello-dati.md). L'ordine di `TABELLE` è l'ordine di caricamento.

Formato intermedio: un file `<tabella>.parquet` per tabella, con le colonne
della tabella. Unica eccezione `results`, divisa in `results.parquet` (gare) e
`sprint_results.parquet` (sprint): stesse colonne, stessa tabella di arrivo.
"""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

_INT = pa.int32()
_TESTO = pa.string()


@dataclass(frozen=True)
class Tabella:
    nome: str
    colonne: tuple[tuple[str, pa.DataType], ...]
    # Bersaglio di ON CONFLICT (vedi docs/modello-dati.md, "Tabelle").
    chiave: tuple[str, ...]
    # Ordinamento delle righe nel Parquet: deve essere totale (deterministico).
    ordine: tuple[str, ...]
    # True: dato derivato, sostituito a ogni caricamento invece dell'upsert.
    sostituita: bool = False
    # Tabella divisa in più file Parquet in base a session_type:
    # (nome del file senza estensione, valore di session_type).
    partizioni: tuple[tuple[str, str], ...] = ()

    @property
    def nomi(self) -> tuple[str, ...]:
        return tuple(n for n, _ in self.colonne)

    @property
    def schema(self) -> pa.Schema:
        return pa.schema([pa.field(n, t) for n, t in self.colonne])

    @property
    def file(self) -> tuple[str, ...]:
        """File Parquet del formato intermedio che alimentano la tabella."""
        if self.partizioni:
            return tuple(f"{nome}.parquet" for nome, _ in self.partizioni)
        return (f"{self.nome}.parquet",)


_SESSIONE = (("race_id", _INT), ("session_type", _TESTO))
_CHIAVE_PILOTA = ("race_id", "session_type", "driver_id")

TABELLE: tuple[Tabella, ...] = (
    Tabella(
        "seasons",
        (("year", _INT), ("wikipedia_url", _TESTO)),
        chiave=("year",),
        ordine=("year",),
    ),
    Tabella(
        "circuits",
        (
            ("id", _INT),
            ("ref", _TESTO),
            ("name", _TESTO),
            ("locality", _TESTO),
            ("country", _TESTO),
            ("latitude", pa.decimal128(9, 6)),
            ("longitude", pa.decimal128(9, 6)),
            ("altitude_m", _INT),
            ("wikipedia_url", _TESTO),
        ),
        chiave=("id",),
        ordine=("id",),
    ),
    Tabella(
        "drivers",
        (
            ("id", _INT),
            ("ref", _TESTO),
            ("given_name", _TESTO),
            ("family_name", _TESTO),
            ("code", _TESTO),
            ("permanent_number", _INT),
            ("date_of_birth", pa.date32()),
            ("nationality", _TESTO),
            ("wikipedia_url", _TESTO),
        ),
        chiave=("id",),
        ordine=("id",),
    ),
    Tabella(
        "constructors",
        (
            ("id", _INT),
            ("ref", _TESTO),
            ("name", _TESTO),
            ("nationality", _TESTO),
            ("wikipedia_url", _TESTO),
        ),
        chiave=("id",),
        ordine=("id",),
    ),
    Tabella(
        "statuses",
        (("id", _INT), ("name", _TESTO)),
        chiave=("id",),
        ordine=("id",),
    ),
    Tabella(
        "races",
        (
            ("id", _INT),
            ("season_year", _INT),
            ("round", _INT),
            ("circuit_id", _INT),
            ("name", _TESTO),
            ("wikipedia_url", _TESTO),
        ),
        chiave=("id",),
        ordine=("id",),
    ),
    Tabella(
        "sessions",
        (
            *_SESSIONE,
            ("session_date", pa.date32()),
            ("start_time_utc", pa.time32("s")),
        ),
        chiave=("race_id", "session_type"),
        ordine=("race_id", "session_type"),
    ),
    Tabella(
        "results",
        (
            *_SESSIONE,
            ("source_id", _INT),
            ("driver_id", _INT),
            ("constructor_id", _INT),
            ("status_id", _INT),
            ("car_number", _INT),
            ("grid_position", _INT),
            ("position", _INT),
            ("position_order", _INT),
            ("outcome", _TESTO),
            ("points", pa.decimal128(6, 2)),
            ("laps_completed", _INT),
            ("time_ms", _INT),
            ("fastest_lap_number", _INT),
            ("fastest_lap_rank", _INT),
            ("fastest_lap_time_ms", _INT),
            ("fastest_lap_speed_kph", pa.decimal128(7, 3)),
        ),
        chiave=("session_type", "source_id"),
        ordine=("race_id", "session_type", "source_id"),
        # Un file per CSV di origine: `results.parquet` contiene le sole gare,
        # come results.csv (lo richiede il test di accettazione sulla
        # validazione, che ne confronta le righe con quelle del CSV).
        partizioni=(("results", "race"), ("sprint_results", "sprint")),
    ),
    Tabella(
        "qualifying_results",
        (
            *_SESSIONE,
            ("driver_id", _INT),
            ("constructor_id", _INT),
            ("car_number", _INT),
            ("position", _INT),
            ("q1_ms", _INT),
            ("q2_ms", _INT),
            ("q3_ms", _INT),
        ),
        chiave=_CHIAVE_PILOTA,
        ordine=_CHIAVE_PILOTA,
    ),
    Tabella(
        "laps",
        (
            *_SESSIONE,
            ("driver_id", _INT),
            ("lap_number", _INT),
            ("position", _INT),
            ("time_ms", _INT),
        ),
        chiave=(*_CHIAVE_PILOTA, "lap_number"),
        ordine=(*_CHIAVE_PILOTA, "lap_number"),
    ),
    Tabella(
        "pit_stops",
        (
            *_SESSIONE,
            ("driver_id", _INT),
            ("stop_number", _INT),
            ("lap_number", _INT),
            ("time_of_day", pa.time32("s")),
            ("duration_ms", _INT),
        ),
        chiave=(*_CHIAVE_PILOTA, "stop_number"),
        ordine=(*_CHIAVE_PILOTA, "stop_number"),
    ),
    Tabella(
        "stints",
        (
            *_SESSIONE,
            ("driver_id", _INT),
            ("stint_number", _INT),
            ("start_lap", _INT),
            ("end_lap", _INT),
            ("compound", _TESTO),
        ),
        chiave=(*_CHIAVE_PILOTA, "stint_number"),
        ordine=(*_CHIAVE_PILOTA, "stint_number"),
        sostituita=True,
    ),
)

PER_NOME: dict[str, Tabella] = {t.nome: t for t in TABELLE}

FILE_SCARTI = "scarti.json"
FILE_ANNULLATI = "valori_annullati.json"
FILE_DERIVATI = "valori_derivati.json"
FILE_PARQUET: tuple[str, ...] = tuple(f for t in TABELLE for f in t.file)
