import logging
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NotificationConfig:
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

class Notifier:
    def __init__(self, config: NotificationConfig | None = None):
        self.config = config or NotificationConfig()

    def send(self, title: str, message: str, url: str = "") -> None:
        self.send_discord(title, message, url)
        self.send_telegram(title, message, url)

    def send_discord(self, title: str, message: str, url: str = "") -> None:
        webhook = self.config.discord_webhook_url
        if not webhook:
            return

        embed = {
            "title": title[:256],
            "description": message[:4096],
            "color": 0x58a6ff,
        }
        if url:
            embed["url"] = url

        try:
            resp = requests.post(
                webhook,
                json={"embeds": [embed]},
                timeout=10,
            )
            if not resp.ok:
                logger.warning(f"Discord webhook error: {resp.status_code}")
        except requests.RequestException as e:
            logger.error(f"Discord webhook failed: {e}")

    def send_telegram(self, title: str, message: str, url: str = "") -> None:
        token = self.config.telegram_bot_token
        chat_id = self.config.telegram_chat_id
        if not token or not chat_id:
            return

        text = f"<b>{title}</b>\n{message}"
        if url:
            text += f"\n<a href='{url}'>Link</a>"

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if not resp.ok:
                logger.warning(f"Telegram error: {resp.status_code} {resp.text[:200]}")
        except requests.RequestException as e:
            logger.error(f"Telegram failed: {e}")

    def send_code_found(self, code_value: str, code_type: str, source: str, title: str, url: str = "") -> None:
        type_icons = {"key": "\U0001F511", "gift_link": "\U0001F381", "giveaway": "\U0001F3B0"}
        icon = type_icons.get(code_type, "\u2728")
        self.send(
            title=f"{icon} New {code_type}: {title[:80]}",
            message=f"Source: {source}\nCode: {code_value[:120]}",
            url=url,
        )
