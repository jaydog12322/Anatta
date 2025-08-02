from __future__ import annotations

"""Utility to load symbol mapping for KRX and NXT dual-listed stocks.

Reads :mod:`config.symbol_map.csv` and returns a list of symbols.
"""

from dataclasses import dataclass
from pathlib import Path
from csv import DictReader
from typing import List

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "symbol_map.csv"


@dataclass(frozen=True)
class Symbol:
    """Represents a dual-listed instrument."""

    krx_code: str
    nxt_code: str
    name: str


def load_symbols(csv_path: Path = CONFIG_PATH) -> List[Symbol]:
    """Load symbol mappings from ``csv_path``.

    Parameters
    ----------
    csv_path:
        Path to a CSV file with columns ``KRX_code``, ``NXT_code``, ``Name``.

    Returns
    -------
    list of :class:`Symbol`
    """

    symbols: List[Symbol] = []
    with csv_path.open(newline="", encoding="utf-8") as csvfile:
        reader = DictReader(csvfile)
        for row in reader:
            symbols.append(
                Symbol(
                    krx_code=row["KRX_code"].strip(),
                    nxt_code=row["NXT_code"].strip(),
                    name=row["Name"].strip(),
                )
            )
    return symbols
