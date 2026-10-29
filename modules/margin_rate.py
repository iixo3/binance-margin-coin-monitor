from __future__ import annotations

import time

from core.util import robust_z

NAME = "margin_rate"


def run(ctx) -> str:
    """Next-hour margin borrow rate for watchlist. Alert on absolute spike or
    robust-z vs stored history."""
    watch = ctx.cfg.get("watchlist", [])
    if not watch:
        return "empty watchlist"
    data = ctx.client.signed_get(
        "/sapi/v1/margin/next-hourly-interest-rate",
        {"assets": ",".join(watch), "isIsolated": "FALSE"},
    )
    ts = int(time.time())
    window = ctx.glob.get("history_window_sec", 604800)
    abs_thr = ctx.cfg.get("rate_alert_hourly", 0.0005)
    z_thr = ctx.cfg.get("rate_z_alert", 3.0)
    parts = []
    for row in data:
        asset = row.get("asset")
        rate = float(row.get("nextHourlyInterestRate", 0.0))
        hist = ctx.store.rate_history(asset, ts - window)
        ctx.store.insert_rate(ts, asset, rate)
        z = robust_z(rate, hist)
        apr = rate * 24 * 365 * 100
        parts.append("%s=%.6f/h (~%.0f%% APR, z=%.1f)" % (asset, rate, apr, z))
        if rate >= abs_thr or z >= z_thr:
            ctx.alert(
                "Margin borrow rate spike: %s" % asset,
                "next hourly %.6f (~%.0f%% APR), z=%.1f" % (rate, apr, z),
            )
    return "; ".join(parts)
