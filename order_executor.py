"""Execute paired orders on KRX and NXT."""

from __future__ import annotations

from typing import Iterable

from spread_detector import TradeIntent


class OrderExecutor:
    """Submit paired orders (stub)."""

    def execute(self, intents: Iterable[TradeIntent]) -> None:
        for intent in intents:
            self._send(intent)

    def _send(self, intent: TradeIntent) -> None:
        raise NotImplementedError("Order submission to Kiwoom pending")
