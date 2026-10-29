from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "monitor.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS inventory (ts INTEGER, asset TEXT, amount REAL);
CREATE INDEX IF NOT EXISTS idx_inv ON inventory(asset, ts);
CREATE TABLE IF NOT EXISTS rate (ts INTEGER, asset TEXT, next_rate REAL);
CREATE INDEX IF NOT EXISTS idx_rate ON rate(asset, ts);
CREATE TABLE IF NOT EXISTS volume (ts INTEGER, symbol TEXT, quote_volume REAL, price_change_pct REAL);
CREATE INDEX IF NOT EXISTS idx_vol ON volume(symbol, ts);
CREATE TABLE IF NOT EXISTS vol_baseline (symbol TEXT PRIMARY KEY, median REAL, mad REAL, n INTEGER, updated INTEGER);
"""


class Store:
    def __init__(self, path: Path = DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- inventory ---
    def insert_inventory(self, ts: int, rows: list) -> None:  # rows: [(asset, amount), ...]
        self.conn.executemany("INSERT INTO inventory VALUES (?,?,?)", [(ts, a, x) for a, x in rows])
        self.conn.commit()

    def rolling_max_inventory(self, asset: str, since_ts: int):
        return self.conn.execute(
            "SELECT MAX(amount) FROM inventory WHERE asset=? AND ts>=?", (asset, since_ts)
        ).fetchone()[0]

    # --- rate ---
    def insert_rate(self, ts: int, asset: str, rate: float) -> None:
        self.conn.execute("INSERT INTO rate VALUES (?,?,?)", (ts, asset, rate))
        self.conn.commit()

    def rate_history(self, asset: str, since_ts: int) -> list:
        rows = self.conn.execute(
            "SELECT next_rate FROM rate WHERE asset=? AND ts>=?", (asset, since_ts)
        ).fetchall()
        return [r[0] for r in rows]

    # --- volume ---
    def insert_volume(self, ts: int, symbol: str, qv: float, pct: float) -> None:
        self.conn.execute("INSERT INTO volume VALUES (?,?,?,?)", (ts, symbol, qv, pct))
        self.conn.commit()

    def get_baseline(self, symbol: str):
        return self.conn.execute(
            "SELECT median, mad, n, updated FROM vol_baseline WHERE symbol=?", (symbol,)
        ).fetchone()  # None or (median, mad, n, updated)

    def set_baseline(self, symbol: str, med: float, mad: float, n: int, updated: int) -> None:
        self.conn.execute("INSERT OR REPLACE INTO vol_baseline VALUES (?,?,?,?,?)",
                          (symbol, med, mad, n, updated))
        self.conn.commit()
