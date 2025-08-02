Design Document (Architecture Overview)
Data Flow

symbol_map.csv → Symbol Loader
                     ↓
              Market-Time Scheduler ← FID215 events
                     ↓
              Data Feed Handler
                     ↓ ticks
              Spread Detector
                     ↓ TradeIntent
              Risk & Exposure Manager
                     ↓
              Order Executor
                     ↓
               Exchanges (KRX/NXT)
                     ↓ fills
              Logger & Monitoring
Process Model

Gateway Process: Hosts the single-threaded Kiwoom OpenAPI session; all TR and order calls are serialized here.

Internal Bus (e.g., in‑process queue): Modules communicate through message passing to avoid thread‑unsafe API calls.

Optional Supervisory Process: Monitors health, restarts gateway on disconnect, and aggregates logs.

Trading Session Handling

Scheduler activates trading only during overlapping KRX/NXT main sessions (09:00:30–15:20) and optional after‑market.

FID 215 events dictate transitions; residual orders are canceled on session close.

Micro‑Batch Execution Strategy

Break available volume into 20–50 share clips (initially 1 share).

After each paired fill, re‑compute spread; abort remaining clips if spread shrinks below threshold.

Any unmatched position triggers immediate market order on opposite exchange.

Risk Controls

Position neutrality: after each cycle, net exposure per symbol must return to zero.

Request throttling: executor queues orders to respect Kiwoom’s 5 req/s limit.

Kill switch: triggers on API disconnect, repeated errors, or cumulative P/L breach.

Logging & Audit

Every market data update, order submission, fill, cancel, and system event is timestamped and stored.

Logs feed a monitoring dashboard displaying spreads, active positions, and request rates.

Alert hooks notify operators of residual positions, API errors, or spread anomalies.

Deployment Considerations

Initial pilot with ~50 symbols to stay within subscription limits; scale to ~200 with multiple screens or sessions.

Live testing uses tiny share size; configuration allows gradual scaling.

No multithreading inside Kiwoom API calls; external modules may run concurrently but interface via message queues.




Module Specifications (final)
Data Feed Handler

Responsibility: Subscribe to KRX (거래소구분=1) and NXT (거래소구분=2 or “_NX” suffix) quote streams; normalize ticks for downstream modules.

Inputs: symbol_map.csv, Kiwoom real-time feeds, FID 215 session events.

Outputs: Per‑symbol order‑book updates pushed onto an internal queue.

Constraints: ≤5 TR requests/s and ≤100 symbols per screen; rotate subscriptions if >200 symbols are tracked.

Parameters: Refresh interval for symbol map, screen grouping, FID 215 session map.

Spread Detector

Responsibility: Maintain best bid/ask for each symbol on both exchanges and emit trade intents when a positive net spread exists.

Inputs: Normalized tick stream; fee schedule (NXT ≈0.0145 %, KRX ≈0.015 %).

Outputs: TradeIntent(symbol, side_a, side_b, qty) when spread > fees + buffer.

Parameters: Buffer (default cost + 0.01 % or ≥1 tick), max 20 trips per symbol/day, 1 share per clip.

Order Executor

Responsibility: Submit paired limit orders, handle micro-batching, and flatten residuals.

Inputs: TradeIntent messages, order acknowledgements.

Outputs: Fill confirmations, residual-position alerts.

Constraints: All Kiwoom calls serialized; SendOrder limited to 5/s; NXT order types 21/22/23/25.

Flow: Buy cheaper leg → upon fill acknowledgment, sell richer leg → re-check spread after each clip → cancel/flatten residuals immediately if spread collapses.

Logger & Monitoring (Slack integration)

Responsibility: Persist every market tick, order event, and error; push critical alerts (residual positions, rate-limit warnings) to Slack.

Inputs: All module events.

Outputs: Structured log files, Slack messages via webhook.

Parameters: Log level, Slack webhook URL, alert filters.

Current Repository Status
config/Pilot_stocklist.csv exists and lists ~50 KOSPI symbols with index and ticker columns. Rename and expand to include KRX_code and future NXT_code columns for the arbitrage engine.

Slack Webhook Setup
Create a Slack app (https://api.slack.com/apps) and enable Incoming Webhooks.

Add the app to the target channel; copy the generated webhook URL.

Store the URL in configuration (e.g., .env as SLACK_WEBHOOK_URL or config/slack.toml).

Logger module posts JSON payloads to this URL whenever critical events occur.