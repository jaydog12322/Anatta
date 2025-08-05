import sys
import traceback
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
    QPlainTextEdit,
)
from PyQt5.QtCore import pyqtSlot, QEventLoop, QTimer
from pykiwoom.kiwoom import Kiwoom

from symbol_loader import load_symbols
from data_feed import Tick
from spread_detector import SpreadDetector
from risk_manager import RiskManager
from order_executor import OrderExecutor


class StatusDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Runtime Status")
        self.text = QPlainTextEdit(readOnly=True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def update_status(self, msg: str) -> None:
        self.text.appendPlainText(msg)


class Feed:
    """Minimal Kiwoom real-time feed wrapper."""

    def __init__(self, kiwoom: Kiwoom, symbols, on_tick, logger):
        self.kw = kiwoom
        self.on_tick = on_tick
        self.log = logger
        self.code_map = {}

        for idx, sym in enumerate(symbols, start=1000):
            screen = f"{idx:04d}"
            self.code_map[sym.krx_code] = (sym, "KRX")
            self.code_map[sym.nxt_code] = (sym, "NXT")
            self.kw.SetRealReg(screen, sym.krx_code, "41;61", "0")
            self.kw.SetRealReg(screen, sym.nxt_code, "41;61", "0")

        handler = getattr(self.kw, "OnReceiveRealData", None)
        if handler is not None:
            try:
                handler.connect(self._handle)  # type: ignore[attr-defined]
            except AttributeError:
                self.kw.OnReceiveRealData = self._handle  # type: ignore[assignment]

    @pyqtSlot(str, str, str)
    def _handle(self, code: str, real_type: str, real_data: str) -> None:
        mapping = self.code_map.get(code)
        if not mapping:
            self.log(f"Unmapped code: {code}")
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
        self.log(f"Raw tick {code}: bid={bid} ask={ask}")
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

        self.executor = None
        self.feed = None
        self.status = StatusDialog()
        self.status.show()

    def log_message(self, text: str) -> None:
        self.log.append(text)
        self.status.update_status(text)

    def load_symbols(self) -> None:
        self.symbols = load_symbols()
        self.log_message(f"Loaded {len(self.symbols)} symbols.")

    def start_test(self) -> None:
        if not self.symbols:
            self.log_message("Load symbols first.")
            return
        try:
            self.log_message("Connecting to Kiwoom…")
            login_loop = QEventLoop()
            login_ok = {"flag": False}

            def _on_login(err_code: int) -> None:
                state = self.kiwoom.GetConnectState()
                self.log_message(f"OnEventConnect err_code={err_code}, state={state}")
                login_ok["flag"] = err_code == 0 and state == 1
                login_loop.quit()

            handler = getattr(self.kiwoom, "OnEventConnect", None)
            if handler is not None:
                try:
                    handler.connect(_on_login)  # type: ignore[attr-defined]
                except AttributeError:
                    self.kiwoom.OnEventConnect = _on_login  # type: ignore[assignment]
            else:
                self.log_message("OnEventConnect handler not found.")
                return

            QTimer.singleShot(
                10000, lambda: (self.log_message("Login timed out"), login_loop.quit())
            )

            self.kiwoom.CommConnect()
            login_loop.exec_()

            if not login_ok["flag"]:
                self.log_message("Login failed; aborting.")
                return

            raw_accounts = self.kiwoom.GetLoginInfo("ACCNO")
            accounts = (
                raw_accounts.split(";") if isinstance(raw_accounts, str) else raw_accounts
            )
            account = accounts[0] if accounts else None
            if not account:
                raise RuntimeError("No Kiwoom account available")
            self.executor = OrderExecutor(session=self.kiwoom, account=account)
            self.log_message(f"Using account {account}")
            self.feed = Feed(self.kiwoom, self.symbols, self.on_tick, self.log_message)
            self.log_message("Subscribed to real-time feed.")
        except Exception as exc:
            msg = f"Start test failed: {exc}\n{traceback.format_exc()}"
            self.log_message(msg)
            print(msg, file=sys.stderr)

    def on_tick(self, tick: Tick) -> None:
        self.log_message(
            f"Tick: {tick.symbol.name} {tick.exchange} bid={tick.bid} ask={tick.ask}"
        )
        intents = self.detector.on_tick(tick)
        for intent in intents:
            if self.risk.approve(intent):
                self.log_message(
                    f"Approved: {intent.symbol.name} "
                    f"{intent.buy_exchange}->{intent.sell_exchange}"
                )
                try:
                    self.executor.execute([intent])
                    self.log_message(
                        f"Executed: {intent.symbol.name} "
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
