"""Daily trading session scheduler."""

from __future__ import annotations

from risk_manager import RiskManager


class DailySessionScheduler:
    """Simple session scheduler for the trading engine."""

    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def start_session(self) -> None:
        """Reset risk limits and prepare for a new session."""
        self.risk_manager.reset_counts()
        # Additional session setup would occur here