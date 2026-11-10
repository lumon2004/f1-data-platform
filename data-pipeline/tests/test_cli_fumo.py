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
    for comando in ("transform", "load", "download", "sample", "run"):
        assert comando in testo


@pytest.mark.parametrize(
    ("comando", "opzioni"),
    [
        ("transform", ["--input", "--output"]),
        ("load", ["--input"]),
        ("download", ["--output", "--force"]),
        ("sample", ["--input", "--output", "--seasons"]),
        ("run", ["--source", "--raw", "--sample", "--processed"]),
    ],
)
def test_help_dei_sottocomandi(capsys, comando, opzioni):
    with pytest.raises(SystemExit) as uscita:
        cli.main([comando, "--help"])
    assert uscita.value.code == 0
    testo = capsys.readouterr().out
    for opzione in opzioni:
        assert opzione in testo


def test_transform_e_implementato(tmp_path, csv_puliti, capsys):
    uscita = tmp_path / "out"
    assert cli.main(["transform", "--input", str(csv_puliti), "--output", str(uscita)]) == 0
    assert (uscita / "results.parquet").is_file() and (uscita / "laps.parquet").is_file()
    assert (uscita / "scarti.json").read_text().strip() == "[]"
    assert "non implementato" not in capsys.readouterr().err


def test_load_e_implementato_e_legge_la_connessione_dall_ambiente(tmp_path, monkeypatch, capsys):
    for nome in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(nome, raising=False)
    assert cli.main(["load", "--input", str(tmp_path)]) == 1
    errore = capsys.readouterr().err
    assert "non implementato" not in errore
    assert "POSTGRES_DB" in errore


def test_scelta_della_sorgente_di_run(tmp_path, csv_puliti):
    vuota = tmp_path / "raw-vuota"
    vuota.mkdir()
    # Senza credenziali Kaggle (vedi conftest): raw se ha dei CSV, altrimenti sample.
    assert cli.scegli_sorgente("auto", csv_puliti, vuota) == csv_puliti
    assert cli.scegli_sorgente("auto", vuota, csv_puliti) == csv_puliti
    assert cli.scegli_sorgente("auto", vuota, vuota) is None
    assert cli.scegli_sorgente("sample", csv_puliti, vuota) is None
    assert cli.scegli_sorgente("sample", vuota, csv_puliti) == csv_puliti
    assert cli.scegli_sorgente("raw", vuota, csv_puliti) is None


def test_run_con_credenziali_scarica_solo_se_raw_e_vuota(tmp_path, csv_puliti, monkeypatch):
    chiamate = []

    def finto(cartella, **_):
        chiamate.append(cartella)
        return 1

    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_finto0123456789")
    monkeypatch.setattr(cli.download_kaggle, "esegui", finto)
    vuota = tmp_path / "raw-vuota"
    vuota.mkdir()
    assert cli.scegli_sorgente("auto", csv_puliti, vuota) == csv_puliti
    assert chiamate == [], "raw contiene già i CSV: nessun download"
    assert cli.scegli_sorgente("auto", vuota, csv_puliti) is None, "download fallito: errore, non ripiego"
    assert chiamate == [vuota]


def test_run_trasforma_poi_carica(tmp_path, csv_puliti, monkeypatch, capsys):
    from f1_pipeline import load

    caricate = []
    monkeypatch.setattr(load, "esegui", lambda cartella: caricate.append(cartella) or 0)
    processed = tmp_path / "processed"
    codice = cli.main(["run", "--source", "sample", "--sample", str(csv_puliti),
                       "--raw", str(tmp_path / "manca"), "--processed", str(processed)])
    assert codice == 0
    assert caricate == [processed]
    assert (processed / "results.parquet").is_file()
    assert f"Sorgente: {csv_puliti}" in capsys.readouterr().out


def test_run_senza_sorgente(tmp_path, capsys):
    assert cli.main(["run", "--raw", str(tmp_path / "a"), "--sample", str(tmp_path / "b"),
                     "--processed", str(tmp_path / "c")]) == 1
    assert "nessun CSV utilizzabile" in capsys.readouterr().err


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
    import psycopg  # noqa: F401
    import pyarrow  # noqa: F401
