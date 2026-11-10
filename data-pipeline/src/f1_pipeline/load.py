"""Sottocomando `load`: carica in PostgreSQL l'output di `transform`.

- Una sola transazione: o entra tutto, o non cambia nulla.
- Idempotente: ogni tabella passa da `COPY` verso una tabella temporanea e poi
  da `INSERT ... ON CONFLICT (chiave) DO UPDATE` verso la tabella vera; le
  righe già identiche non vengono riscritte. `stints`, dato derivato, viene
  sostituita per le gare presenti nell'input.
- Non crea tabelle: lo schema nasce dalle migrazioni (le applica il backend).
  Se manca, il comando si ferma con un messaggio chiaro.
- Connessione dalle sole variabili d'ambiente `POSTGRES_HOST`, `POSTGRES_PORT`,
  `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg import sql

from f1_pipeline.tabelle import FILE_PARQUET, TABELLE, Tabella

VARIABILI = ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
# Chiave del lock consultivo: due caricamenti contemporanei si mettono in fila.
_LOCK = 0x46315F50  # "F1_P"


class ErroreCaricamento(Exception):
    """Errore previsto: il messaggio è già pronto per l'utente."""


def parametri_connessione(ambiente: Mapping[str, str] | None = None) -> dict[str, object]:
    """Parametri di connessione dalle variabili d'ambiente (mai i valori nei messaggi)."""
    if ambiente is None:
        ambiente = os.environ
    valori = {nome: (ambiente.get(nome) or "").strip() for nome in VARIABILI}
    valori["POSTGRES_HOST"] = valori["POSTGRES_HOST"] or "localhost"
    valori["POSTGRES_PORT"] = valori["POSTGRES_PORT"] or "5432"
    mancanti = [nome for nome, valore in valori.items() if not valore]
    if mancanti:
        raise ErroreCaricamento(
            "variabili d'ambiente mancanti per la connessione a PostgreSQL: "
            + ", ".join(mancanti)
        )
    try:
        porta = int(valori["POSTGRES_PORT"])
    except ValueError:
        raise ErroreCaricamento("POSTGRES_PORT non è un numero di porta") from None
    return {
        "host": valori["POSTGRES_HOST"],
        "port": porta,
        "dbname": valori["POSTGRES_DB"],
        "user": valori["POSTGRES_USER"],
        "password": valori["POSTGRES_PASSWORD"],
        "connect_timeout": 15,
        "application_name": "f1-pipeline",
    }


def leggi_input(cartella: Path) -> dict[str, object]:
    """Legge i Parquet e ne controlla le colonne prima di toccare il database."""
    cartella = Path(cartella)
    if not cartella.is_dir():
        raise ErroreCaricamento(f"la cartella di input {cartella} non esiste")
    mancanti = [f for f in FILE_PARQUET if not (cartella / f).is_file()]
    if mancanti:
        raise ErroreCaricamento(
            f"in {cartella} mancano: {', '.join(mancanti)}. "
            "L'input di load è l'output di `f1-pipeline transform`."
        )
    dati = {}
    for tabella in TABELLE:
        parti = []
        for file in tabella.file:
            letta = pq.read_table(cartella / file)
            if tuple(letta.column_names) != tabella.nomi:
                raise ErroreCaricamento(
                    f"{file}: colonne {letta.column_names}, attese {list(tabella.nomi)}"
                )
            try:
                parti.append(letta.cast(tabella.schema))
            except (pa.ArrowInvalid, pa.ArrowNotImplementedError) as errore:
                raise ErroreCaricamento(f"{file}: tipi delle colonne inattesi ({errore})") from None
        dati[tabella.nome] = pa.concat_tables(parti)
    return dati


def _controlla_schema(cur: psycopg.Cursor) -> None:
    cur.execute(
        "SELECT nome FROM unnest(%s::text[]) AS t(nome) WHERE to_regclass(quote_ident(nome)) IS NULL",
        ([t.nome for t in TABELLE],),
    )
    assenti = [riga[0] for riga in cur.fetchall()]
    if assenti:
        raise ErroreCaricamento(
            "lo schema del database non è pronto: mancano le tabelle "
            + ", ".join(assenti)
            + ". La pipeline non crea tabelle: lo schema nasce dalle migrazioni di "
            "database/migrations/, applicate dal backend all'avvio. Avvia prima il backend."
        )


def _carica_tabella(cur: psycopg.Cursor, tabella: Tabella, dati) -> int:
    """COPY in una tabella temporanea, poi upsert (o sostituzione). Restituisce le righe toccate."""
    nome = sql.Identifier(tabella.nome)
    temporanea = sql.Identifier(f"_carica_{tabella.nome}")
    colonne = sql.SQL(", ").join(sql.Identifier(c) for c in tabella.nomi)
    cur.execute(
        sql.SQL(
            "CREATE TEMP TABLE {tmp} ON COMMIT DROP AS SELECT {colonne} FROM {nome} WITH NO DATA"
        ).format(tmp=temporanea, colonne=colonne, nome=nome)
    )
    valori = [colonna.to_pylist() for colonna in dati.columns]
    with cur.copy(
        sql.SQL("COPY {tmp} ({colonne}) FROM STDIN").format(tmp=temporanea, colonne=colonne)
    ) as copia:
        for riga in zip(*valori):
            copia.write_row(riga)

    ordine = sql.SQL(", ").join(sql.Identifier(c) for c in tabella.chiave)
    if tabella.sostituita:
        # Dato derivato: si sostituiscono le righe delle gare presenti nell'input.
        cur.execute(
            sql.SQL("DELETE FROM {nome} WHERE race_id IN (SELECT id FROM {gare})").format(
                nome=nome, gare=sql.Identifier("_carica_races")
            )
        )
        cur.execute(
            sql.SQL(
                "INSERT INTO {nome} ({colonne}) SELECT {colonne} FROM {tmp} ORDER BY {ordine}"
            ).format(nome=nome, colonne=colonne, tmp=temporanea, ordine=ordine)
        )
        return cur.rowcount

    altre = [c for c in tabella.nomi if c not in tabella.chiave]
    aggiorna = sql.SQL(", ").join(
        sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(c)) for c in altre
    )
    attuali = sql.SQL(", ").join(sql.SQL("{t}.{c}").format(t=nome, c=sql.Identifier(c)) for c in altre)
    nuove = sql.SQL(", ").join(sql.SQL("EXCLUDED.{c}").format(c=sql.Identifier(c)) for c in altre)
    cur.execute(
        sql.SQL(
            "INSERT INTO {nome} ({colonne}) SELECT {colonne} FROM {tmp} ORDER BY {ordine} "
            "ON CONFLICT ({ordine}) DO UPDATE SET {aggiorna} "
            "WHERE ({attuali}) IS DISTINCT FROM ({nuove})"
        ).format(
            nome=nome, colonne=colonne, tmp=temporanea, ordine=ordine,
            aggiorna=aggiorna, attuali=attuali, nuove=nuove,
        )
    )
    return cur.rowcount


def carica(cartella: Path, ambiente: Mapping[str, str] | None = None) -> dict[str, tuple[int, int]]:
    """Carica l'output di transform. Restituisce {tabella: (righe in input, righe scritte)}."""
    parametri = parametri_connessione(ambiente)
    dati = leggi_input(cartella)
    try:
        conn = psycopg.connect(**parametri)
    except psycopg.OperationalError as errore:
        raise ErroreCaricamento(
            f"connessione a PostgreSQL non riuscita ({parametri['host']}:{parametri['port']}, "
            f"database {parametri['dbname']}): {str(errore).strip()}"
        ) from None
    esito: dict[str, tuple[int, int]] = {}
    try:
        with conn:  # una transazione: commit alla fine, rollback su errore; poi chiude
            with conn.cursor() as cur:
                _controlla_schema(cur)
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK,))
                for tabella in TABELLE:
                    letta = dati[tabella.nome]
                    esito[tabella.nome] = (letta.num_rows, _carica_tabella(cur, tabella, letta))
    except psycopg.Error as errore:
        vincolo = getattr(getattr(errore, "diag", None), "constraint_name", None)
        raise ErroreCaricamento(
            "caricamento annullato, nessuna modifica al database: "
            + str(errore).strip()
            + (f" [vincolo {vincolo}]" if vincolo else "")
        ) from None
    # Statistiche aggiornate per il pianificatore dopo un caricamento in blocco:
    # un'ottimizzazione, quindi un suo errore non annulla il caricamento.
    try:
        with psycopg.connect(**parametri, autocommit=True) as conn, conn.cursor() as cur:
            for tabella in TABELLE:
                cur.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(tabella.nome)))
    except psycopg.Error as errore:
        print(f"Avviso: ANALYZE non riuscito: {str(errore).strip()}", file=sys.stderr)
    return esito


def esegui(cartella: Path, ambiente: Mapping[str, str] | None = None) -> int:
    """Logica del sottocomando. Restituisce il codice di uscita."""
    inizio = time.monotonic()
    try:
        esito = carica(cartella, ambiente)
    except ErroreCaricamento as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1
    print("Tabella                righe input   inserite o aggiornate")
    for nome, (righe, scritte) in esito.items():
        print(f"  {nome:20s} {righe:>10d} {scritte:>10d}")
    print(f"Caricamento completato in {time.monotonic() - inizio:.1f} s")
    return 0
