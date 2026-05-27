import logging
import re
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TELEGRAM_PUBLIC_CHANNELS = [
    "steamgamesfree",
    "FreeSteamKeys",
    "steamgiveawaysfree",
    "freegamessteam",
]

TELEGRAM_PROXY = "https://t.me/s/{}"

class TelegramScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def search_channels(self) -> list[dict]:
        results = []
        for channel in TELEGRAM_PUBLIC_CHANNELS:
            try:
                posts = self._scrape_channel(channel)
                results.extend(posts)
            except Exception as e:
                logger.error(f"Telegram channel {channel} error: {e}")
        return results

    def _scrape_channel(self, channel: str) -> list[dict]:
        resp = self.session.get(TELEGRAM_PROXY.format(channel), timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for msg in soup.select(".tgme_widget_message_wrap")[:20]:
            text_el = msg.select_one(".tgme_widget_message_text")
            if not text_el:
                continue

            text = text_el.text.strip()
            link_el = msg.select_one("a.tgme_widget_message_date")
            msg_url = link_el.get("href", "") if link_el else ""

            giveaway_keywords = [
                "free", "giveaway", "key", "steam", "code",
                "gratis", "regalo", "sorteo", "chave",
            ]
            if not any(kw in text.lower() for kw in giveaway_keywords):
                continue

            results.append({
                "source": f"telegram/{channel}",
                "source_url": msg_url,
                "title": text[:200],
                "description": text[:2000],
                "found_at": datetime.now(timezone.utc).isoformat(),
            })

        return results
