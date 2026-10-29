# Binance Margin Coin Monitor

A small local tool that watches Binance margin data for chosen coins and flags signs that traders are piling into short positions.

Every few minutes it reads three things, stores them in a local SQLite file, and compares each new reading with the recent past:

- **Lending pool:** how much of a coin Binance still has available to lend on margin. A pool that drains fast means borrowers (usually short sellers) are taking it.
- **Borrow rate:** the next-hour interest rate for borrowing the coin. A jump means borrowing demand is rising.
- **Trading volume:** the coin's 24-hour volume against its usual daily volume. A spike means unusual activity.

It only reads data. It never places orders or moves funds.

## How it works

One small core (Binance client, config, storage, alerts) and three independent signal modules, each switched on or off in `config.json`:

| Module | Binance data | Key needed? | Flags when |
|---|---|---|---|
| `margin_inventory` | `/sapi/v1/margin/available-inventory` (all coins, one call) | yes, read-only | the pool falls a set share below its highest level in the recent window |
| `margin_rate` | `/sapi/v1/margin/next-hourly-interest-rate` (watchlist) | yes, read-only | the rate passes a fixed level, or is far above its own recent history |
| `volume_zscore` | `/api/v3/ticker/24hr` and daily `/api/v3/klines` | no (public) | 24 h volume is far above the median of the last N days |

"Far above" uses a robust z-score (median and median absolute deviation), so one past spike does not distort the baseline. With too little history it stays quiet instead of raising false alarms.

Alerts print to the console. Telegram messages are optional and stay muted until switched on.

Plain Python 3, standard library only: no packages to install.

```
run.py               command line: p0 / once / loop
core/
  binance_client.py  public and signed (HMAC-SHA256) GET requests
  config.py          reads config.json and .env
  store.py           SQLite tables for each signal
  notify.py          console and optional Telegram alerts
  util.py            robust z-score
modules/
  margin_inventory.py
  margin_rate.py
  volume_zscore.py
data/monitor.db      sample run (see below); new readings are added here
```

## Run it

1. Copy `.env.example` to `.env` and add a Binance API key with **reading permission only** (no trading, no withdrawals; limiting it to your IP address is recommended). The volume module works without a key; to run without one, switch the two margin modules off in `config.json`.
2. Optional: add a Telegram bot token and chat ID to `.env`, then set `"alerts_enabled": true` in `config.json`.
3. Run one of:

```
python3 run.py p0      # check the key and print the current PHA lending pool and the five largest pools
python3 run.py once    # one reading of every enabled module (for a scheduler such as cron)
python3 run.py loop    # keep reading every poll_interval_sec seconds; Ctrl-C to stop
```

## Settings (`config.json`)

- `poll_interval_sec`: time between readings in `loop` mode (default 300).
- `history_window_sec`: how far back the recent window reaches (default 7 days).
- `alerts_enabled`: `false` prints what would have fired, marked as muted.
- `margin_inventory.watchlist`, `drained_alert_pct`: coins to check, and the drop from the window's highest level that triggers an alert (0.5 = 50%).
- `margin_rate.watchlist`, `rate_alert_hourly`, `rate_z_alert`: coins to check, fixed hourly-rate level, z-score level.
- `volume_zscore.symbols`, `baseline_days`, `z_alert`: trading pairs, days in the baseline, z-score level.

The included settings watch PHA (pair PHAUSDT). The lending-pool module stores every coin Binance returns, so adding coins to its watchlist costs no extra calls; the rate and volume modules make calls per coin.

## Sample data

`data/monitor.db` holds a real run from 4 to 5 June 2026 (about 34 hours, one reading every 5 minutes): about 159,000 lending-pool readings across 406 coins, plus the PHA borrow rate and PHAUSDT volume (and one earlier volume reading from 2 June). Delete it to start fresh; the tool creates a new one on first run.

## Limits

- The lending pool is the amount Binance has set aside to lend; it can move in coarse steps, so thresholds should be tuned on observed data before trusting them.
- The volume baseline compares the last 24 hours with daily totals; it does not adjust for time of day.
- It runs on one machine: while that machine is off, the history has gaps, which weakens the baselines.

## Credit

Built by iixo3. Shared to view, not to reuse: no licence is granted.
