from __future__ import annotations

import time
from statistics import median

NAME = "volume_zscore"


def _baseline(ctx, symbol: str, days: int):
    """Daily quote-volume baseline from 1d klines (drops in-progress candle)."""
    candles = ctx.client.public_get(
        "/api/v3/klines", {"symbol": symbol, "interval": "1d", "limit": days + 1}
    )
    closed = candles[:-1] if len(candles) > 1 else candles
    qv = [float(c[7]) for c in closed]  # index 7 = quote asset volume
    if len(qv) < 5:
        return None
    med = median(qv)
    mad = median([abs(x - med) for x in qv])
    return med, mad, len(qv)


def run(ctx) -> str:
    """24h quote volume vs N-day median/MAD baseline. Public data, no key."""
    symbols = ctx.cfg.get("symbols", [])
    days = ctx.cfg.get("baseline_days", 30)
    z_thr = ctx.cfg.get("z_alert", 3.0)
    if not symbols:
        return "no symbols"

    tickers = ctx.client.public_get("/api/v3/ticker/24hr")
    tmap = {t["symbol"]: t for t in tickers}
    ts = int(time.time())
    parts = []
    for sym in symbols:
        t = tmap.get(sym)
        if not t:
            parts.append("%s=MISSING" % sym)
            continue
        qv = float(t["quoteVolume"])
        pct = float(t["priceChangePercent"])
        ctx.store.insert_volume(ts, sym, qv, pct)

        base = ctx.store.get_baseline(sym)
        if not base or (ts - base[3]) > 86400:  # refresh once a day
            b = _baseline(ctx, sym, days)
            if b:
                ctx.store.set_baseline(sym, b[0], b[1], b[2], ts)
                base = (b[0], b[1], b[2], ts)
        z = 0.6745 * (qv - base[0]) / base[1] if (base and base[1] > 0) else 0.0
        parts.append("%s qv=%.4g (z=%.1f, chg=%.1f%%)" % (sym, qv, z, pct))
        if z >= z_thr:
            ctx.alert(
                "Volume spike: %s" % sym,
                "24h quote vol %.4g, z=%.1f vs %dd median, price %.1f%%" % (qv, z, days, pct),
            )
    return "; ".join(parts)
