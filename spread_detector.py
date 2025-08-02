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
        self.book: Dict[tuple[str, str], Tick] = {}

    def on_tick(self, tick: Tick) -> list[TradeIntent]:
        """Update internal state with *tick* and emit trade intents.

                Ticks are stored keyed by ``(symbol.krx_code, exchange)``. When both
                KRX and NXT quotes are available for a symbol, the function computes the
                cross-exchange spreads and, if profitable beyond fees plus a buffer,
                returns the corresponding :class:`TradeIntent` objects.
                """

        # store the latest tick for this symbol/exchange pair
        self.book[(tick.symbol.krx_code, tick.exchange)] = tick

        krx_tick = self.book.get((tick.symbol.krx_code, "KRX"))
        nxt_tick = self.book.get((tick.symbol.krx_code, "NXT"))

        intents: list[TradeIntent] = []
        threshold = self.fees + self.buffer

        if krx_tick and nxt_tick:
            # Buy on KRX, sell on NXT
            spread_kn = (nxt_tick.bid - krx_tick.ask) / krx_tick.ask
            if spread_kn > threshold:
                intents.append(
                    TradeIntent(
                        symbol=tick.symbol,
                        buy_exchange="KRX",
                        sell_exchange="NXT",
                        qty=1,
                    )
                )

            # Buy on NXT, sell on KRX
            spread_nk = (krx_tick.bid - nxt_tick.ask) / nxt_tick.ask
            if spread_nk > threshold:
                intents.append(
                    TradeIntent(
                        symbol=tick.symbol,
                        buy_exchange="NXT",
                        sell_exchange="KRX",
                        qty=1,
                    )
                )

        return intents
