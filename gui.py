import os
import sys
import traceback
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import pyqtSlot
from pykiwoom.kiwoom import Kiwoom

from symbol_loader import load_symbols
from data_feed import Tick
from spread_detector import SpreadDetector
from risk_manager import RiskManager
from order_executor import OrderExecutor


class Feed:
    """Minimal Kiwoom real‑time feed wrapper."""

    def __init__(self, kiwoom: Kiwoom, symbols, on_tick):
        self.kw = kiwoom
        self.on_tick = on_tick
        self.code_map = {}

        for idx, sym in enumerate(symbols, start=1000):
            screen = f"{idx:04d}"
            self.code_map[sym.krx_code] = (sym, "KRX")
            self.code_map[sym.nxt_code] = (sym, "NXT")
            self.kw.SetRealReg(screen, sym.krx_code, "41;61", "0")
            self.kw.SetRealReg(screen, sym.nxt_code, "41;61", "0")

        self.kw.OnReceiveRealData.connect(self._handle)

    @pyqtSlot(str, str, str)
    def _handle(self, code: str, _type: str, _data: str) -> None:
        mapping = self.code_map.get(code)
        if not mapping:
            return
        sym, exch = mapping
        try:
            bid = float(self.kw.GetCommRealData(code, 61).strip() or 0)
        except Exception:
            bid = 0.0
        try:
            ask = float(self.kw.GetCommRealData(code, 41).strip() or 0)
        except Exception:
            ask = 0.0
        self.on_tick(Tick(symbol=sym, exchange=exch, bid=bid, ask=ask))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anatta Arbitrage Tester")

        self.log = QTextEdit(readOnly=True)
        self.load_btn = QPushButton("Load Symbols")
        self.start_btn = QPushButton("Start Test")
        self.load_btn.clicked.connect(self.load_symbols)
        self.start_btn.clicked.connect(self.start_test)

        layout = QVBoxLayout()
        layout.addWidget(self.load_btn)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.log)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.symbols = []
        self.kiwoom = Kiwoom()
        self.detector = SpreadDetector()
        self.risk = RiskManager()

        account = os.getenv("KIWOOM_ACCOUNT", "YOUR_ACCOUNT")
        if account == "YOUR_ACCOUNT":
            raise ValueError("Set KIWOOM_ACCOUNT before running.")
        account = os.getenv("KIWOOM_ACCOUNT", "YOUR_ACCOUNT")
        if account == "YOUR_ACCOUNT":
            raise ValueError("Set KIWOOM_ACCOUNT before running.")

        self.executor = OrderExecutor(session=self.kiwoom, account=account)
        self.feed = None

    def log_message(self, text: str) -> None:
        self.log.append(text)

    def load_symbols(self) -> None:
        self.symbols = load_symbols()
        self.log_message(f"Loaded {len(self.symbols)} symbols.")

    def start_test(self) -> None:
        if not self.symbols:
            self.log_message("Load symbols first.")
            return
        try:
            self.log_message("Connecting to Kiwoom…")
            self.kiwoom.CommConnect()
            self.feed = Feed(self.kiwoom, self.symbols, self.on_tick)
            self.log_message("Subscribed to real-time feed.")
        except Exception as exc:
            msg = f"Start test failed: {exc}\n{traceback.format_exc()}"
            self.log_message(msg)
            print(msg, file=sys.stderr)

    def on_tick(self, tick: Tick) -> None:
        self.log_message(
            f"Tick: {tick.symbol.ticker} {tick.exchange} bid={tick.bid} ask={tick.ask}"
        )
        intents = self.detector.on_tick(tick)
        for intent in intents:
            if self.risk.approve(intent):
                self.log_message(
                    f"Approved: {intent.symbol.ticker} "
                    f"{intent.buy_exchange}->{intent.sell_exchange}"
                )
                try:
                    self.executor.execute([intent])
                    self.log_message(
                        f"Executed: {intent.symbol.ticker} "
                        f"{intent.buy_exchange}->{intent.sell_exchange} "
                        f"qty={intent.qty}"
                    )
                except NotImplementedError:
                    self.log_message("OrderExecutor._send not implemented.")
                except Exception as exc:
                    self.log_message(f"Execution error: {exc}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
