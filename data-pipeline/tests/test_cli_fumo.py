"""Test di fumo dello scheletro: la CLI esiste e rispetta il contratto."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from f1_pipeline import cli


def test_help_elenca_i_sottocomandi(capsys):
    with pytest.raises(SystemExit) as uscita:
        cli.main(["--help"])
    assert uscita.value.code == 0
    testo = capsys.readouterr().out
    for comando in ("transform", "load", "download"):
        assert comando in testo


@pytest.mark.parametrize(
    ("comando", "opzioni"),
    [
        ("transform", ["--input", "--output"]),
        ("load", ["--input"]),
        ("download", ["--output"]),
    ],
)
def test_help_dei_sottocomandi(capsys, comando, opzioni):
    with pytest.raises(SystemExit) as uscita:
        cli.main([comando, "--help"])
    assert uscita.value.code == 0
    testo = capsys.readouterr().out
    for opzione in opzioni:
        assert opzione in testo


@pytest.mark.parametrize(
    "argv",
    [
        ["transform", "--input", "in", "--output", "out"],
        ["load", "--input", "in"],
        ["download", "--output", "out"],
    ],
)
def test_sottocomandi_non_ancora_implementati(capsys, argv):
    assert cli.main(argv) != 0
    catturato = capsys.readouterr()
    assert "non implementato" in catturato.err
    assert catturato.out == ""


def test_senza_sottocomando_e_un_errore(capsys):
    with pytest.raises(SystemExit) as uscita:
        cli.main([])
    assert uscita.value.code != 0


def test_transform_richiede_input_e_output(capsys):
    with pytest.raises(SystemExit) as uscita:
        cli.main(["transform", "--input", "in"])
    assert uscita.value.code != 0


def test_entry_point_installato():
    eseguibile = shutil.which("f1-pipeline")
    assert eseguibile, "il comando f1-pipeline non è nel PATH"
    esito = subprocess.run(
        [eseguibile, "--help"], capture_output=True, text=True, check=False
    )
    assert esito.returncode == 0
    assert "transform" in esito.stdout


def test_dipendenze_importabili():
    import polars  # noqa: F401
    import psycopg  # noqa: F401
    import pyarrow  # noqa: F401
