#MA5 Strategy Integration Plan
##1. Overview
This document outlines how to incorporate the MA5/MA10 moving‑average strategy into Samsara Trader while keeping resource usage low and preserving the existing “Run Trade Test” workflow.

##2. Required Inputs
2.1 Watchlist
File: watchlist.csv

Each row: stock code; assumed to have already passed trigger and reset filters.

2.2 Historical Price Cache
Store last 10 closing prices per symbol (CSV or JSON under data/cache/).

Allows rapid MA5/MA10 computation without repeated historical API calls.

##3. Runtime Components
3.1 Data Structures
Symbol State	Purpose
deque(maxlen=10)	Rolling window of closes for MA5/MA10
waiting_for_entry	True until position opened
in_position	True when holding shares
target_price	Derived from MA spread
unfilled_order	Tracks open limit orders to prevent duplicates
max_drawdown, max_gain	Recorded while in position
3.2 Strategy Class
MA5Strategy derived from StrategyBase

Implements:

on_start: load watchlist & price cache, request any missing days via TR.

on_tick: update deque with current price, recompute MA5/MA10, decide entry/exit.

on_end: flush updated deque back to cache.

3.3 Workflow Integration
“🧪 Run Trade Test” button → run_trading_test() → instantiates MA5Strategy.

MarketDataManager normalizes Kiwoom real‑time tick data and calls strategy.on_tick.

OrderManager sends limit buy/sell orders based on strategy decisions.

##4. Algorithm Details
4.1 Entry Conditions
waiting_for_entry is True.

Compute MA5 and MA10:

If current price dips below MA5 while remaining above MA10:

Gap-down below MA5 at open → buy at open.

Intraday cross below MA5 → buy at MA5.

Otherwise → buy at current price.

Set target_price = entry_price * (1 + (MA5 - MA10)/MA10).

Flip in_position to True and initialize drawdown/gain tracking.

4.2 Exit Conditions
For each tick while in_position:

Update MA10 from deque.

Check order:

If market opens below MA10 → exit immediately at open.

If price >= target_price before touching MA10 → win at target.

If price <= MA10 or MA10 touched anytime → loss at MA10 (or open if gap down).

Record max drawdown and max gain.

After exit, set waiting_for_entry and in_position to False for that symbol (post-trade reset assumed handled externally).

4.3 Order Throttling
Maintain an “open order” flag per symbol to avoid duplicate limit orders while awaiting fills.

Future work: partial fill tracking.

##5. Daily Rollover
Program is restarted each morning.

On startup: load cached closes; request only missing days to update deques.

At market close: append final close to deques and write cache to disk.

##6. Resource Considerations
≤100 symbols → 10 floats each → <1 MB RAM.

Deques avoid unbounded memory growth.

Minimal TR requests: 1 per symbol at startup plus any missing days.

##7. Open Questions / Next Steps
Persistence format: CSV vs JSON; one file per symbol vs combined.

API rate limiting: Determine stagger interval between initial TR calls.

Error handling: What to do when price feed is interrupted or order fails?

Testing harness: Incorporate unit tests for deque logic and entry/exit state transitions.

##8. Implementation Sequence
Implement data/cache loading/saving utility.

Create MA5Strategy class with state management and MA calculations.

Hook MA5Strategy into run_trading_test.

Add order‑throttling logic for open orders.

Validate with manual runs; later integrate automated tests.

This plan should serve as the reference for coding the MA5/MA10 strategy within the existing Samsara Trader framework. Let me know when you're ready to proceed with implementation.