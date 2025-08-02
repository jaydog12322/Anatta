"""Basic exposure checks for the arbitrage engine."""

from __future__ import annotations

from spread_detector import TradeIntent


class RiskManager:
    """Enforce simple per-symbol limits."""

    def __init__(self, max_trips: int = 20):
        self.max_trips = max_trips
        self.counts: dict[str, int] = {}

    def approve(self, intent: TradeIntent) -> bool:
        key = intent.symbol.krx_code
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= self.max_trips
