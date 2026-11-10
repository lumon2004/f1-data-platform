"""Normalizzazione dei valori: marcatori di NULL, numeri, date, orari, tempi."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from f1_pipeline import normalizza as nz


@pytest.mark.parametrize(
    ("grezzo", "atteso"),
    [(r"\N", None), ("", None), ("  ", None), (None, None), (" Argentinian ", "Argentinian"), ("0", "0")],
)
def test_pulisci(grezzo, atteso):
    assert nz.pulisci(grezzo) == atteso


@pytest.mark.parametrize(("testo", "atteso"), [("0", 0), ("42", 42), ("-7", -7), ("+3", 3)])
def test_intero(testo, atteso):
    assert nz.intero(testo) == atteso


@pytest.mark.parametrize("testo", ["abc", "1.0", "1e3", "12 3", "2147483648", "٣"])
def test_intero_non_valido(testo):
    with pytest.raises(nz.NonValido):
        nz.intero(testo)


def test_decimale_esatto_e_arrotondato():
    assert nz.decimale("12.5", 6, 2) == Decimal("12.50")
    assert nz.decimale("0.005", 6, 2) == Decimal("0.01")
    assert nz.decimale("218.300", 7, 3) == Decimal("218.300")
    assert isinstance(nz.decimale("25", 6, 2), Decimal)


@pytest.mark.parametrize("testo", ["abc", "1,5", "nan", "inf", "10000", "1e2"])
def test_decimale_non_valido(testo):
    with pytest.raises(nz.NonValido):
        nz.decimale(testo, 6, 2)


def test_data_e_ora():
    assert nz.data("2023-03-05") == dt.date(2023, 3, 5)
    assert nz.ora("15:00:00") == dt.time(15, 0, 0)
    for sbagliata in ("2023-02-30", "05/03/2023", "2023-3-5"):
        with pytest.raises(nz.NonValido):
            nz.data(sbagliata)
    for sbagliata in ("25:00:00", "15:00", "15:61:00", "abc"):
        with pytest.raises(nz.NonValido):
            nz.ora(sbagliata)


@pytest.mark.parametrize(
    ("testo", "ms"),
    [
        ("1:27.452", 87452),
        ("26.898", 26898),
        ("17:23.456", 1043456),
        ("2:05:05.152", 7505152),
        ("0:59.9", 59900),
    ],
)
def test_tempo_ms(testo, ms):
    assert nz.tempo_ms(testo) == ms


@pytest.mark.parametrize("testo", ["abc", "1:27", "1:75.000", "1:2:3:4.000", "+5.478s", "-1.000"])
def test_tempo_ms_non_valido(testo):
    with pytest.raises(nz.NonValido):
        nz.tempo_ms(testo)
