"""Riga di comando `f1-pipeline`.

Scheletro della tappa 1: i sottocomandi esistono con le opzioni fissate dal
contratto dei test di accettazione, ma la logica arriva alla tappa 3.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from f1_pipeline import __version__

PROG = "f1-pipeline"

# Codice di uscita dei sottocomandi non ancora implementati (diverso da 0 e
# dal 2 che argparse usa per gli errori di sintassi).
EXIT_NON_IMPLEMENTATO = 1


def _non_implementato(args: argparse.Namespace) -> int:
    print(f"{PROG} {args.comando}: non implementato", file=sys.stderr)
    return EXIT_NON_IMPLEMENTATO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Pipeline dati di F1 Data Platform: dai CSV Kaggle/Ergast al "
            "formato intermedio Parquet e a PostgreSQL."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"{PROG} {__version__}"
    )
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO", required=True)

    download = sub.add_parser(
        "download",
        help="scarica il dataset dalla sorgente remota (richiede le credenziali)",
        description=(
            "Scarica il dataset nella cartella indicata. Le credenziali si "
            "leggono dalla configurazione dell'utente, mai dal codice."
        ),
    )
    download.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella in cui salvare i CSV grezzi",
    )
    download.set_defaults(func=_non_implementato)

    transform = sub.add_parser(
        "transform",
        help="valida e normalizza i CSV e scrive Parquet e scarti.json",
        description=(
            "Legge i CSV in formato Kaggle/Ergast da --input e scrive in "
            "--output un file <tabella>.parquet per tabella e il report "
            "degli scarti scarti.json."
        ),
    )
    transform.add_argument(
        "--input",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella con i CSV in formato Kaggle/Ergast",
    )
    transform.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella del formato intermedio",
    )
    transform.set_defaults(func=_non_implementato)

    load = sub.add_parser(
        "load",
        help="carica in PostgreSQL l'output di transform (idempotente)",
        description=(
            "Carica in PostgreSQL l'output di transform con upsert sulle "
            "chiavi naturali. Connessione da POSTGRES_HOST, POSTGRES_PORT, "
            "POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD."
        ),
    )
    load.add_argument(
        "--input",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella con l'output di transform",
    )
    load.set_defaults(func=_non_implementato)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
