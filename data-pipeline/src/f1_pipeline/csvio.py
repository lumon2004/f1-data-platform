"""Lettura dei CSV Kaggle/Ergast.

La numerazione dei record è quella del contratto degli scarti: l'intestazione
è la riga 1, il primo record la riga 2; le righe completamente vuote non si
contano (come fa `csv.DictReader`).
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

# utf-8-sig: tollera un eventuale BOM in testa al file.
CODIFICA = "utf-8-sig"


class ErroreInput(Exception):
    """Input inutilizzabile nel suo insieme: il messaggio è per l'utente."""


def leggi_record(percorso: Path) -> Iterator[tuple[list[str], str]]:
    """Record di un CSV come (campi, testo originale del record).

    Il testo originale permette di ricopiare un record byte per byte (serve al
    campionamento), anche quando un campo tra virgolette contiene un a capo.
    """
    with open(percorso, newline="", encoding=CODIFICA) as f:
        consumate: list[str] = []

        def righe() -> Iterator[str]:
            for riga in f:
                consumate.append(riga)
                yield riga

        for campi in csv.reader(righe()):
            testo = "".join(consumate)
            consumate.clear()
            if campi:
                yield campi, testo


def leggi_csv(
    percorso: Path,
    obbligatorie: tuple[str, ...] = (),
) -> tuple[list[str], Iterator[tuple[int, dict[str, str] | None]]]:
    """Intestazione e record di un CSV, letti per nome di colonna.

    Restituisce (intestazione, iteratore di (numero di riga, record)). Un
    record con un numero di campi diverso dall'intestazione arriva come `None`.
    """
    record = leggi_record(percorso)
    try:
        intestazione, _ = next(record)
    except StopIteration:
        raise ErroreInput(f"{percorso.name}: file vuoto, manca l'intestazione") from None
    intestazione = [c.strip() for c in intestazione]
    mancanti = [c for c in obbligatorie if c not in intestazione]
    if mancanti:
        raise ErroreInput(
            f"{percorso.name}: colonne mancanti nell'intestazione: {', '.join(mancanti)}"
        )

    def righe() -> Iterator[tuple[int, dict[str, str] | None]]:
        attesi = len(intestazione)
        for numero, (campi, _) in enumerate(record, start=2):
            if len(campi) != attesi:
                yield numero, None
            else:
                yield numero, dict(zip(intestazione, campi))

    return intestazione, righe()
