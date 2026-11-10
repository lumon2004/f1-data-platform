"""Conversioni dei valori testuali dei CSV Kaggle/Ergast in valori tipizzati.

Ogni funzione riceve un testo già ripulito (vedi `pulisci`) e solleva
`NonValido` se il testo non rappresenta un valore del tipo atteso: decide il
chiamante se la riga va scartata o se il solo attributo diventa NULL.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Marcatori di valore mancante della fonte.
MARCATORI_NULL = frozenset({"", r"\N"})

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1

_INTERO = re.compile(r"[+-]?\d+", re.ASCII)
_DECIMALE = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)", re.ASCII)
_DATA = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_ORA = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})", re.ASCII)
_TEMPO = re.compile(r"(?:(?:(\d+):)?(\d+):)?(\d+)\.(\d{1,3})", re.ASCII)


class NonValido(ValueError):
    """Il testo non rappresenta un valore del tipo atteso."""


def pulisci(valore: str | None) -> str | None:
    """Toglie gli spazi ai bordi; `\\N` e stringa vuota diventano `None`."""
    if valore is None:
        return None
    valore = valore.strip()
    return None if valore in MARCATORI_NULL else valore


def intero(testo: str) -> int:
    """Intero a 32 bit (il tipo `integer` dello schema)."""
    if not _INTERO.fullmatch(testo):
        raise NonValido("non è un intero")
    numero = int(testo)
    if not INT32_MIN <= numero <= INT32_MAX:
        raise NonValido("intero fuori dall'intervallo a 32 bit")
    return numero


def decimale(testo: str, cifre: int, decimali: int) -> Decimal:
    """Decimale esatto per una colonna `numeric(cifre, decimali)`.

    Le cifre decimali in eccesso si arrotondano; un valore con troppe cifre
    intere non è valido.
    """
    if not _DECIMALE.fullmatch(testo):
        raise NonValido("non è un numero decimale")
    try:
        numero = Decimal(testo).quantize(
            Decimal(1).scaleb(-decimali), rounding=ROUND_HALF_UP
        )
    except InvalidOperation:
        raise NonValido("non è un numero decimale") from None
    if abs(numero) >= Decimal(10) ** (cifre - decimali):
        raise NonValido(f"troppo grande per numeric({cifre},{decimali})")
    return numero


def data(testo: str) -> dt.date:
    """Data ISO `aaaa-mm-gg`."""
    if not _DATA.fullmatch(testo):
        raise NonValido("non è una data aaaa-mm-gg")
    try:
        return dt.date.fromisoformat(testo)
    except ValueError:
        raise NonValido("data inesistente") from None


def ora(testo: str) -> dt.time:
    """Orario `hh:mm:ss`."""
    trovato = _ORA.fullmatch(testo)
    if not trovato:
        raise NonValido("non è un orario hh:mm:ss")
    ore, minuti, secondi = (int(g) for g in trovato.groups())
    if ore > 23 or minuti > 59 or secondi > 59:
        raise NonValido("orario inesistente")
    return dt.time(ore, minuti, secondi)


def tempo_ms(testo: str) -> int:
    """Tempo o durata testuale in millisecondi.

    Formati della fonte: `ss.mmm`, `m:ss.mmm` e `h:mm:ss.mmm`.
    """
    trovato = _TEMPO.fullmatch(testo)
    if not trovato:
        raise NonValido("non è un tempo m:ss.mmm")
    ore, minuti, secondi, frazione = trovato.groups()
    if minuti is not None and int(secondi) > 59:
        raise NonValido("secondi oltre 59")
    if ore is not None and int(minuti) > 59:
        raise NonValido("minuti oltre 59")
    totale = (
        (int(ore or 0) * 60 + int(minuti or 0)) * 60 + int(secondi)
    ) * 1000 + int(frazione.ljust(3, "0"))
    if totale > INT32_MAX:
        raise NonValido("tempo fuori dall'intervallo a 32 bit")
    return totale
