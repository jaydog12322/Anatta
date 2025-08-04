from __future__ import annotations

"""Simple PyQt5 interface for testing spread detection pipeline."""

import sys
from typing import List

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

import symbol_loader
from data_feed import Tick, DataFeedHandler
from spread_detector import SpreadDetector, TradeIntent
from risk_manager import RiskManager
from order_executor import OrderExecutor


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anatta Test GUI")

        # Core components
        self.symbols: List[symbol_loader.Symbol] = []
        self.data_feed: DataFeedHandler | None = None
        self.detector: SpreadDetector | None = None
        self.risk_manager: RiskManager | None = None
        self.executor: OrderExecutor | None = None

        # UI setup
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Symbols")
        self.start_btn = QPushButton("Start Test")
        self.reset_btn = QPushButton("Reset")
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        # Connections
        self.load_btn.clicked.connect(self.load_symbols)
        self.start_btn.clicked.connect(self.start_test)
        self.reset_btn.clicked.connect(self.reset_session)

        # Timer for feeding ticks
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.feed_tick)

        # Tick queue
        self.ticks: List[Tick] = []

    # ------------------------------------------------------------------
    def load_symbols(self) -> None:
        """Load symbol mappings and log the result."""
        self.symbols = symbol_loader.load_symbols()
        self.log.append(f"Loaded {len(self.symbols)} symbols.")

    # ------------------------------------------------------------------
    def start_test(self) -> None:
        """Instantiate components and begin tick simulation."""
        if not self.symbols:
            self.load_symbols()

        self.data_feed = DataFeedHandler(self.symbols)
        self.detector = SpreadDetector()
        self.risk_manager = RiskManager()
        self.executor = OrderExecutor()
        # Patch executor send method to avoid NotImplementedError
        if self.executor:
            self.executor._send = self._log_send  # type: ignore[attr-defined]

        symbol = self.symbols[0]
        self.ticks = [
            Tick(symbol, "KRX", bid=99.5, ask=100.0),
            Tick(symbol, "NXT", bid=101.0, ask=101.5),
            Tick(symbol, "NXT", bid=99.0, ask=99.5),
            Tick(symbol, "KRX", bid=100.5, ask=101.0),
        ]
        self.log.append("Starting tick feed...")
        self.timer.start(500)

    # ------------------------------------------------------------------
    def feed_tick(self) -> None:
        if not self.ticks:
            self.timer.stop()
            self.log.append("Feed complete.")
            return

        tick = self.ticks.pop(0)
        self.log.append(
            f"Tick: {tick.symbol.krx_code} {tick.exchange} bid={tick.bid} ask={tick.ask}"
        )

        intents = self.detector.on_tick(tick) if self.detector else []
        approved: List[TradeIntent] = []
        for intent in intents:
            if self.risk_manager and self.risk_manager.approve(intent):
                approved.append(intent)
                self.log.append(
                    f"Approved: {intent.symbol.krx_code} {intent.buy_exchange}->{intent.sell_exchange}"
                )
            else:
                self.log.append(
                    f"Rejected: {intent.symbol.krx_code} {intent.buy_exchange}->{intent.sell_exchange}"
                )

        if approved and self.executor:
            try:
                self.executor.execute(approved)
            except NotImplementedError:
                self.log.append("Order execution not implemented.")

    # ------------------------------------------------------------------
    def reset_session(self) -> None:
        if self.risk_manager:
            self.risk_manager.reset_counts()
        self.timer.stop()
        self.ticks.clear()
        self.log.append("Session reset.")

    # ------------------------------------------------------------------
    def _log_send(self, intent: TradeIntent) -> None:
        self.log.append(
            f"Executed: {intent.symbol.krx_code} {intent.buy_exchange}->{intent.sell_exchange} qty={intent.qty}"
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()