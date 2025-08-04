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
        """Start the Kiwoom real-time data feed.

        The handler connects to the Kiwoom OpenAPI and registers real-time
        quote updates for both the KRX and NXT codes of each symbol provided
        at construction time. Incoming data is normalised into :class:`Tick`
        objects and dispatched via an ``on_tick`` callback if one is present.

        Notes
        -----
        * The Kiwoom OCX control must live in the main thread.  Therefore this
          function blocks in the Qt event loop and must be invoked from the
          application entry point.
        * ``pykiwoom`` is preferred, but the code falls back to a direct
          ``win32com`` dispatch when unavailable.
        """

        # Import PyQt lazily to avoid mandatory dependency during unit tests.
        from PyQt5.QtCore import QEventLoop
        from PyQt5.QtWidgets import QApplication

        # ------------------------------------------------------------------
        # Instantiate QApplication (required for the OCX control) in the main
        # thread and create the Kiwoom control.
        app = QApplication.instance() or QApplication([])

        try:  # Prefer pykiwoom when available
            from pykiwoom.kiwoom import Kiwoom  # type: ignore

            kiwoom = Kiwoom()
        except Exception:  # pragma: no cover - best effort fallback
            # Fallback for environments without pykiwoom.  This path requires
            # ``win32com.client`` which is only available on Windows.
            from win32com.client import Dispatch  # type: ignore

            kiwoom = Dispatch("KHOPENAPI.KHOpenAPICtrl.1")

        # ------------------------------------------------------------------
        # Log-in phase. CommConnect triggers the OnEventConnect callback when
        # the login process finishes. We spin a temporary event loop waiting
        # for that signal to fire.
        login_loop = QEventLoop()

        def _on_login(_err_code: int) -> None:
            login_loop.quit()

        # ``connect`` is available when using pykiwoom.  In a raw COM dispatch
        # we simply assign the event handler attribute.
        try:  # pragma: no branch - attribute availability is environment specific
            kiwoom.OnEventConnect.connect(_on_login)  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover - COM fallback
            kiwoom.OnEventConnect = _on_login  # type: ignore[assignment]

        kiwoom.CommConnect()
        login_loop.exec_()

        # ------------------------------------------------------------------
        # Prepare symbol lookup and register real-time feeds.  ``SetRealReg``
        # associates a screen number with each code and requests the best bid
        # and ask fields (FIDs 61 and 41 respectively).
        code_map: dict[str, tuple[Symbol, str]] = {}
        for idx, sym in enumerate(self.symbols, start=1000):
            screen_no = f"{idx:04d}"
            code_map[sym.krx_code] = (sym, "KRX")
            code_map[sym.nxt_code] = (sym, "NXT")

            kiwoom.SetRealReg(screen_no, sym.krx_code, "41;61", "0")
            kiwoom.SetRealReg(screen_no, sym.nxt_code, "41;61", "0")

        # ------------------------------------------------------------------
        # Real-time data handler.  Normalise the bid/ask prices into our
        # ``Tick`` structure and forward to an ``on_tick`` callback when
        # provided by the consumer.
        def _on_receive_real_data(code: str, real_type: str, _data: str) -> None:
            mapping = code_map.get(code)
            if not mapping:
                return
            symbol, exchange = mapping

            # FID 61: best bid, FID 41: best ask. ``GetCommRealData`` returns
            # strings which may include sign characters; ``strip`` removes
            # whitespace before conversion.
            try:
                bid = float(kiwoom.GetCommRealData(code, 61).strip())
            except Exception:  # pragma: no cover - malformed data
                bid = 0.0
            try:
                ask = float(kiwoom.GetCommRealData(code, 41).strip())
            except Exception:  # pragma: no cover - malformed data
                ask = 0.0

            tick = Tick(symbol=symbol, exchange=exchange, bid=bid, ask=ask)
            callback = getattr(self, "on_tick", None)
            if callable(callback):
                callback(tick)

        try:  # pragma: no branch
            kiwoom.OnReceiveRealData.connect(_on_receive_real_data)  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover - COM fallback
            kiwoom.OnReceiveRealData = _on_receive_real_data  # type: ignore[assignment]

        # ------------------------------------------------------------------
        # Enter the main Qt event loop; this blocks the calling thread, which is
        # required when interacting with the Kiwoom OCX control.
        app.exec_()
