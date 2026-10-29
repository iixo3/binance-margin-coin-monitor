from __future__ import annotations

import time

NAME = "margin_inventory"


def run(ctx) -> str:
    """Margin lendable pool (all assets, 1 call). Store all; evaluate watchlist
    drained% vs rolling-max baseline."""
    data = ctx.client.signed_get("/sapi/v1/margin/available-inventory", {"type": "MARGIN"})
    assets = data.get("assets", {})
    ts = int(time.time())
    ctx.store.insert_inventory(ts, [(a, float(x)) for a, x in assets.items()])

    window = ctx.glob.get("history_window_sec", 604800)
    thr = ctx.cfg.get("drained_alert_pct", 0.5)
    parts = []
    for asset in ctx.cfg.get("watchlist", []):
        cur = float(assets.get(asset, 0.0))
        mx = ctx.store.rolling_max_inventory(asset, ts - window) or cur
        drained = (mx - cur) / mx if mx > 0 else 0.0
        parts.append("%s=%.4g (win-max %.4g, drained %.0f%%)" % (asset, cur, mx, drained * 100))
        if drained >= thr:
            ctx.alert(
                "Margin inventory drained: %s" % asset,
                "available %.4g, down %.0f%% from %dd max %.4g" % (cur, drained * 100, window // 86400, mx),
            )
    return ("stored %d assets; " % len(assets)) + ("; ".join(parts) if parts else "no watchlist")
