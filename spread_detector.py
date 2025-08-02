"""Spread detection logic for cross-exchange arbitrage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from symbol_loader import Symbol
from data_feed import Tick


@dataclass
class TradeIntent:
    symbol: Symbol
    buy_exchange: str
    sell_exchange: str
    qty: int


class SpreadDetector:
    """Calculate spreads and emit trade intents."""

    def __init__(self, fees: float = 0.00035, buffer: float = 0.0001):
        self.fees = fees
        self.buffer = buffer
        self.book: Dict[str, Tick] = {}

    def on_tick(self, tick: Tick) -> list[TradeIntent]:
        self.book[tick.exchange + tick.symbol.krx_code] = tick
        # placeholder logic
        return []
