"""Riga di comando `f1-pipeline`.

Sottocomandi: `download` (dataset Kaggle), `sample` (dataset di esempio),
`transform` (CSV -> Parquet + report degli scarti), `load` (Parquet ->
PostgreSQL) e `run`, che li concatena: è il comando unico che riproduce la
pipeline. Le opzioni di `transform` e `load` sono fissate dal contratto dei
test di accettazione.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from f1_pipeline import __version__
from f1_pipeline import download as download_kaggle

PROG = "f1-pipeline"

# Cartelle predefinite di `run`: variabili d'ambiente (impostate nell'immagine
# Docker), altrimenti i nomi relativi usati dentro data-pipeline/.
VAR_RAW, VAR_SAMPLE, VAR_PROCESSED = "F1_RAW_DIR", "F1_SAMPLE_DIR", "F1_PROCESSED_DIR"


def _cartella(variabile: str, predefinita: str) -> Path:
    return Path(os.environ.get(variabile) or predefinita)


def _download(args: argparse.Namespace) -> int:
    return download_kaggle.esegui(args.output, force=args.force)


def _sample(args: argparse.Namespace) -> int:
    from f1_pipeline import sample

    return sample.esegui(args.input, args.output, args.seasons)


def _transform(args: argparse.Namespace) -> int:
    from f1_pipeline import transform

    return transform.esegui(args.input, args.output)


def _load(args: argparse.Namespace) -> int:
    from f1_pipeline import load

    return load.esegui(args.input)


def scegli_sorgente(sorgente: str, raw: Path, sample: Path) -> Path | None:
    """Cartella dei CSV da usare per `run`; `None` se non ce n'è una utilizzabile.

    `auto`: con credenziali Kaggle nell'ambiente scarica il dataset in `raw`
    (se non c'è già); poi usa i CSV di `raw` se presenti, altrimenti `sample`.
    """
    if sorgente == "sample":
        return sample if download_kaggle.csv_presenti(sample) else None
    if sorgente == "auto" and not download_kaggle.csv_presenti(raw):
        try:
            credenziali = download_kaggle.leggi_credenziali()
        except download_kaggle.ErroreDownload as errore:
            print(f"Errore: {errore}", file=sys.stderr)
            return None
        if credenziali is not None and download_kaggle.esegui(raw) != 0:
            return None
    if download_kaggle.csv_presenti(raw):
        return raw
    if sorgente == "auto" and download_kaggle.csv_presenti(sample):
        return sample
    return None


def _run(args: argparse.Namespace) -> int:
    from f1_pipeline import load, transform

    sorgente = scegli_sorgente(args.source, args.raw, args.sample)
    if sorgente is None:
        print(
            f"Errore: nessun CSV utilizzabile (sorgente: {args.source}; "
            f"raw: {args.raw}; sample: {args.sample}).",
            file=sys.stderr,
        )
        return 1
    print(f"Sorgente: {sorgente}", flush=True)
    codice = transform.esegui(sorgente, args.processed)
    if codice != 0:
        return codice
    sys.stdout.flush()
    return load.esegui(args.processed)


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
        help="scarica il dataset da Kaggle (richiede le credenziali)",
        description=(
            f"Scarica il dataset Kaggle {download_kaggle.DATASET} e ne estrae "
            "i CSV direttamente nella cartella indicata. Le credenziali si "
            "leggono solo dalle variabili d'ambiente: il token singolo "
            "KAGGLE_API_TOKEN, oppure la coppia KAGGLE_USERNAME + KAGGLE_KEY. "
            "Se la cartella contiene già dei CSV non riscarica nulla."
        ),
    )
    download.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella in cui salvare i CSV grezzi",
    )
    download.add_argument(
        "--force",
        action="store_true",
        help="riscarica e sovrascrive anche se la cartella contiene già dei CSV",
    )
    download.set_defaults(func=_download)

    sample = sub.add_parser(
        "sample",
        help="estrae dal dataset completo il dataset di esempio",
        description=(
            "Copia da --input in --output i soli record delle stagioni "
            "indicate, nel formato originale Kaggle/Ergast, con le sole "
            "anagrafiche citate. Stesso input, stesso output."
        ),
    )
    sample.add_argument(
        "--input", type=Path, required=True, metavar="DIR",
        help="cartella con i CSV del dataset completo",
    )
    sample.add_argument(
        "--output", type=Path, required=True, metavar="DIR",
        help="cartella del dataset di esempio",
    )
    sample.add_argument(
        "--seasons", type=int, nargs="+", required=True, metavar="ANNO",
        help="stagioni da includere (es. 2022 2023 2024)",
    )
    sample.set_defaults(func=_sample)

    transform = sub.add_parser(
        "transform",
        help="valida e normalizza i CSV e scrive Parquet e scarti.json",
        description=(
            "Legge i CSV in formato Kaggle/Ergast da --input e scrive in "
            "--output un file <tabella>.parquet per tabella (results diviso in "
            "results.parquet per le gare e sprint_results.parquet), il report "
            "delle righe scartate scarti.json e l'elenco degli attributi "
            "facoltativi messi a NULL valori_annullati.json e quello delle "
            "posizioni ricavate da positionText valori_derivati.json."
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
    transform.set_defaults(func=_transform)

    load = sub.add_parser(
        "load",
        help="carica in PostgreSQL l'output di transform (idempotente)",
        description=(
            "Carica in PostgreSQL l'output di transform con upsert sulle "
            "chiavi naturali, in una sola transazione. Lo schema deve "
            "esistere già (migrazioni). Connessione da POSTGRES_HOST, "
            "POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD."
        ),
    )
    load.add_argument(
        "--input",
        type=Path,
        required=True,
        metavar="DIR",
        help="cartella con l'output di transform",
    )
    load.set_defaults(func=_load)

    run = sub.add_parser(
        "run",
        help="pipeline completa: sorgente, transform e load in un solo comando",
        description=(
            "Sceglie la sorgente, poi esegue transform e load. Con --source "
            "auto: se nell'ambiente ci sono le credenziali Kaggle e --raw non "
            "contiene CSV, scarica il dataset in --raw; usa i CSV di --raw se "
            "presenti, altrimenti quelli di --sample. Cartelle predefinite "
            f"dalle variabili {VAR_RAW}, {VAR_SAMPLE}, {VAR_PROCESSED}."
        ),
    )
    run.add_argument(
        "--source", choices=("auto", "raw", "sample"), default="auto",
        help="auto (predefinita), raw (solo dataset completo) o sample (solo dataset di esempio)",
    )
    run.add_argument(
        "--raw", type=Path, default=_cartella(VAR_RAW, "raw"), metavar="DIR",
        help="cartella dei CSV del dataset completo (predefinita: %(default)s)",
    )
    run.add_argument(
        "--sample", type=Path, default=_cartella(VAR_SAMPLE, "sample"), metavar="DIR",
        help="cartella del dataset di esempio (predefinita: %(default)s)",
    )
    run.add_argument(
        "--processed", type=Path, default=_cartella(VAR_PROCESSED, "processed"), metavar="DIR",
        help="cartella del formato intermedio (predefinita: %(default)s)",
    )
    run.set_defaults(func=_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
