"""Real-time market data feed handler for KRX and NXT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from symbol_loader import Symbol


@dataclass
class Tick:
    symbol: Symbol
    exchange: str
    bid: float
    ask: float


class DataFeedHandler:
    """Subscribe to Kiwoom feeds and emit normalized ticks."""

    def __init__(self, symbols: Iterable[Symbol]):
        self.symbols = list(symbols)

    def run(self) -> None:
        """Start the feed loop (placeholder)."""
        raise NotImplementedError("Kiwoom integration pending")
