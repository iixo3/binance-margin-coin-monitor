from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.binance.com"


class BinanceClient:
    """Thin Binance REST client: public + SIGNED (HMAC-SHA256) GET.

    Stdlib only. Signed calls need a READ-ONLY key (Enable Reading).
    """

    def __init__(self, api_key: str = "", api_secret: str = "", recv_window: int = 5000):
        self.api_key = api_key
        self.api_secret = api_secret
        self.recv_window = recv_window
        self._offset = 0
        self._synced = False

    def _get(self, url: str, headers: dict = None):
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise RuntimeError("HTTP %s from %s -> %s" % (e.code, url.split("?")[0], body))

    def public_get(self, path: str, params: dict = None):
        qs = ("?" + urllib.parse.urlencode(params)) if params else ""
        return self._get(BASE + path + qs)

    def _sync_time(self):
        data = self.public_get("/api/v3/time")
        self._offset = int(data["serverTime"]) - int(time.time() * 1000)
        self._synced = True

    def signed_get(self, path: str, params: dict = None):
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Signed call needs BINANCE_API_KEY / BINANCE_API_SECRET in .env")
        if not self._synced:
            self._sync_time()
        p = dict(params or {})
        p["timestamp"] = int(time.time() * 1000) + self._offset
        p["recvWindow"] = self.recv_window
        qs = urllib.parse.urlencode(p)
        sig = hmac.new(self.api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        url = BASE + path + "?" + qs + "&signature=" + sig
        return self._get(url, headers={"X-MBX-APIKEY": self.api_key})
