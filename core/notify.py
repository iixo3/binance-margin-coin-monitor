from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime


class Notifier:
    """Console + optional Telegram. Telegram fires only when enabled AND
    a bot token + chat_id are configured."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def _telegram(self, text: str) -> bool:
        if not (self.bot_token and self.chat_id):
            return False
        url = "https://api.telegram.org/bot%s/sendMessage" % self.bot_token
        data = urllib.parse.urlencode(
            {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        ).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as r:
                json.load(r)
            return True
        except urllib.error.HTTPError as e:
            print("[notify] telegram error:", e.read().decode("utf-8", "replace"))
            return False

    def alert(self, title: str, body: str, enabled: bool) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = "[%s] ALERT: %s | %s" % (stamp, title, body)
        if not enabled:
            print(line + "  -> (muted: alerts_enabled=false)")
            return
        sent = self._telegram("*%s*\n%s" % (title, body))
        print(line + ("  -> telegram sent" if sent else "  -> (telegram not configured)"))
