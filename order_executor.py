"""Execute paired orders on KRX and NXT."""

from __future__ import annotations

import queue
import time
from collections import deque
from typing import Iterable

from spread_detector import TradeIntent


class OrderError(Exception):
    """Raised when an order cannot be confirmed or is rejected."""


class OrderExecutor:
    """Submit paired orders through the Kiwoom OpenAPI session.

    The executor serialises all calls to :func:`SendOrder` and rate limits
    them to the Kiwoom mandated ``≤5`` requests per second.  Fill
    confirmations are obtained from ``OnReceiveChejanData`` events.
    """

    def __init__(self, session, account: str):
        self.session = session
        self.account = account

        # Track timestamps for rudimentary rate limiting (≤5 req/s).
        self._req_times: deque[float] = deque(maxlen=5)

        # Queue filled by ``OnReceiveChejanData`` for order status updates.
        self._chejan_q: queue.Queue[dict] = queue.Queue()

        # Register callback if the session exposes the signal (Qt style).
        handler = getattr(self.session, "OnReceiveChejanData", None)
        if handler is not None:
            try:  # pragma: no cover - depends on runtime environment
                handler.connect(self._on_chejan)  # type: ignore[attr-defined]
            except Exception:
                # Mock objects used during testing may not provide ``connect``.
                pass

    # ------------------------------------------------------------------
    # Event handling utilities
    # ------------------------------------------------------------------
    def _on_chejan(self, gubun, item_cnt, fid_list):  # pragma: no cover - Qt callback
        """Callback for Kiwoom "chejan" (order/fill) events.

        The function extracts the instrument code and status from the Kiwoom
        session via :func:`GetChejanData` and places them on a local queue to
        be consumed by :meth:`_wait_for_fill`.
        """

        getter = getattr(self.session, "GetChejanData", None)
        data = {"gubun": gubun}
        if getter is not None:
            data["code"] = getter(9001)  # FID for instrument code
            data["status"] = getter(913)  # FID for order status
            data["error"] = getter(919)  # FID for error code/message
        self._chejan_q.put(data)

    def _throttle(self) -> None:
        """Block until a Kiwoom request slot is available."""

        if len(self._req_times) == self._req_times.maxlen:
            delta = time.time() - self._req_times[0]
            if delta < 1:
                time.sleep(1 - delta)
        self._req_times.append(time.time())

    def execute(self, intents: Iterable[TradeIntent]) -> None:
        for intent in intents:
            self._send(intent)

    # ------------------------------------------------------------------
    # Order submission helpers
    # ------------------------------------------------------------------
    def _submit_and_wait(self, code: str, side: str, qty: int) -> None:
        """Send an order and wait for fill confirmation."""

        order_type = 1 if side.upper() == "BUY" else 2
        self._throttle()
        ret = self.session.SendOrder(  # type: ignore[attr-defined]
            "anatta",  # sRQName
            "0000",  # sScreenNo
            self.account,
            order_type,
            code,
            qty,
            0,  # nPrice; 0 for market orders
            "03",  # sHogaGb: market
            "",  # sOrgOrderNo
        )
        if ret != 0:
            raise OrderError(f"SendOrder failed with code {ret}")

        # Wait for matching chejan event confirming execution.
        end = time.time() + 5
        while time.time() < end:
            try:
                event = self._chejan_q.get(timeout=end - time.time())
            except queue.Empty:
                break
            if event.get("code") == code:
                if event.get("error"):
                    raise OrderError(str(event["error"]))
                return  # confirmed
        raise OrderError("No fill confirmation received")

    # ------------------------------------------------------------------


    def _send(self, intent: TradeIntent) -> None:
        raise NotImplementedError("Order submission to Kiwoom pending")
        """Submit paired orders and recover from failures.

                Orders are sent sequentially: the cheaper leg is bought first; upon
                confirmation the opposing leg is sold.  If the second leg fails, a
                market order is issued to flatten the residual position on the first
                exchange.
                """

        buy_code = (
            intent.symbol.krx_code if intent.buy_exchange == "KRX" else intent.symbol.nxt_code
        )
        sell_code = (
            intent.symbol.krx_code if intent.sell_exchange == "KRX" else intent.symbol.nxt_code
        )

        # Step 1: execute the buy leg and wait for confirmation.
        self._submit_and_wait(buy_code, "BUY", intent.qty)

        # Step 2: attempt to execute the sell leg.  If this fails, issue a
        # flattening order to offset the filled buy leg.
        try:
            self._submit_and_wait(sell_code, "SELL", intent.qty)
        except OrderError:
            try:
                self._submit_and_wait(buy_code, "SELL", intent.qty)
            except OrderError:
                # If flattening also fails we simply propagate the error; an
                # external risk manager should handle any residual exposure.
                pass
            raise