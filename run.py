from __future__ import annotations

import argparse
import importlib
import time
import traceback
from datetime import datetime

from core.binance_client import BinanceClient
from core.config import env, load_config
from core.notify import Notifier
from core.store import Store

MODULE_NAMES = ["margin_inventory", "margin_rate", "volume_zscore"]


class Ctx:
    def __init__(self, client, store, notify, mod_cfg, glob, alerts_enabled):
        self.client = client
        self.store = store
        self.notify = notify
        self.cfg = mod_cfg
        self.glob = glob
        self.alerts_enabled = alerts_enabled

    def alert(self, title, body):
        self.notify.alert(title, body, self.alerts_enabled)


def build():
    cfg = load_config()
    client = BinanceClient(env("BINANCE_API_KEY"), env("BINANCE_API_SECRET"))
    store = Store()
    notify = Notifier(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"))
    return cfg, client, store, notify


def run_once(cfg, client, store, notify):
    alerts = cfg.get("alerts_enabled", False)
    mods = cfg.get("modules", {})
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name in MODULE_NAMES:
        mcfg = mods.get(name, {})
        if not mcfg.get("enabled", False):
            continue
        mod = importlib.import_module("modules." + name)
        ctx = Ctx(client, store, notify, mcfg, cfg, alerts)
        try:
            print("[%s] %s -> %s" % (stamp, name, mod.run(ctx)))
        except Exception as e:
            print("[%s] %s -> ERROR: %s" % (stamp, name, e))
            traceback.print_exc()


def cmd_p0(client):
    print("P0: reading margin available-inventory (validates key + shows live numbers)...")
    data = client.signed_get("/sapi/v1/margin/available-inventory", {"type": "MARGIN"})
    assets = data.get("assets", {})
    print("updateTime:", data.get("updateTime"), "| assets returned:", len(assets))
    print("  PHA available to borrow:", assets.get("PHA", "(not listed)"))
    top = sorted(((float(v), k) for k, v in assets.items()), reverse=True)[:5]
    print("  largest pools:", ", ".join("%s=%.4g" % (k, v) for v, k in top))


def main():
    ap = argparse.ArgumentParser(description="Binance margin + volume monitor")
    ap.add_argument("cmd", choices=["p0", "once", "loop"],
                    help="p0=validate key + read PHA; once=one tick (cron); loop=continuous")
    args = ap.parse_args()
    cfg, client, store, notify = build()
    if args.cmd == "p0":
        cmd_p0(client)
    elif args.cmd == "once":
        run_once(cfg, client, store, notify)
    elif args.cmd == "loop":
        interval = cfg.get("poll_interval_sec", 300)
        print("loop: every %ds | alerts_enabled=%s | Ctrl-C to stop"
              % (interval, cfg.get("alerts_enabled", False)))
        while True:
            run_once(cfg, client, store, notify)
            time.sleep(interval)


if __name__ == "__main__":
    main()
