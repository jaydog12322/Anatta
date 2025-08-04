from pykiwoom.kiwoom import Kiwoom

class DataFeedHandler:
    def __init__(self, symbols):
        self.symbols = list(symbols)
        self.kw = Kiwoom()
        self.kw.CommConnect()

    def run(self):
        for i, sym in enumerate(self.symbols):
            screen = f"000{i:02d}"
            self.kw.SetRealReg(screen, sym.krx_code, "41;42", "0")  # bid/ask FIDs
            self.kw.SetRealReg(screen, sym.nxt_code, "41;42", "0")

        @self.kw.OnReceiveRealData.connect
        def _on_real(code, real_type, data):
            bid = float(self.kw.GetCommRealData(code, 41)) / 100
            ask = float(self.kw.GetCommRealData(code, 42)) / 100
            exch = "NXT" if code.endswith("_NX") else "KRX"
            tick = Tick(symbol=_find_symbol(code), exchange=exch, bid=bid, ask=ask)
            intents = detector.on_tick(tick)
            approved = [i for i in intents if risk.approve(i)]
            executor.execute(approved)

        self.kw._app.exec_()  # start event loop
