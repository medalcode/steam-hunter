import logging
import requests
import json
import re

logger = logging.getLogger(__name__)

ASF_IPC_DEFAULT = "http://localhost:1243"

TRANSIENT_ERRORS = [
    "rate limit", "RateLimit", "429", "too many requests",
    "Timeout", "timed out", "timeout",
    "not connect", "Connection refused", "refused",
    "throttle", "Throttle",
    "Offline", "not logged", "NotLoggedOn",
]

class ASFClient:
    def __init__(self, ipc_url: str = ASF_IPC_DEFAULT, password: str = ""):
        self.ipc_url = ipc_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if password:
            self.session.headers.update({"Authentication": password})

    def _do_request(self, method: str, path: str, data: dict | None = None):
        url = f"{self.ipc_url}{path}"
        try:
            resp = self.session.request(method, url, json=data, timeout=10)

            if resp.status_code == 403:
                return {"success": False, "error": "ASF returned 403 - check IPC password"}
            if resp.status_code == 404:
                return {"success": False, "error": "ASF endpoint not found (404)"}
            if not resp.ok:
                return {"success": False, "error": f"ASF error {resp.status_code}: {resp.text[:200]}"}

            return resp.json()
        except requests.ConnectionError:
            return {"success": False, "error": f"Cannot connect to ASF at {self.ipc_url}"}
        except requests.Timeout:
            return {"success": False, "error": "ASF request timed out"}
        except Exception as e:
            return {"success": False, "error": f"ASF error: {e}"}

    @staticmethod
    def _is_transient(error_message: str) -> bool:
        if not error_message:
            return False
        return any(t in error_message for t in TRANSIENT_ERRORS)

    def get_bots(self) -> list[dict]:
        result = self._do_request("GET", "/api/bot")
        if isinstance(result, dict) and "Result" in result:
            bots = result["Result"]
            if isinstance(bots, list):
                return [
                    {
                        "name": b.get("BotName", b.get("Name", "?")),
                        "status": b.get("Status", "?"),
                        "games": b.get("CardsFarmer", {}).get("CurrentGamesFarming", 0),
                        "online": b.get("Status") == 1,
                    }
                    for b in bots
                ]
        if isinstance(result, list):
            return [
                {
                    "name": b.get("BotName", b.get("Name", "?")),
                    "status": b.get("Status", "?"),
                    "games": b.get("CardsFarmer", {}).get("CurrentGamesFarming", 0),
                    "online": b.get("Status") == 1,
                }
                for b in result
            ]
        return []

    def get_bot_status(self, bot: str) -> dict:
        result = self._do_request("GET", f"/api/bot/{bot}")
        if isinstance(result, dict) and "Result" in result:
            return {
                "name": result["Result"].get("BotName", bot),
                "status": result["Result"].get("Status", "?"),
                "online": result["Result"].get("Status") == 1,
            }
        return {}

    def send_command(self, bot: str, command: str) -> dict:
        return self._do_request(
            "POST",
            "/api/command",
            data={"command": f"{command} {bot}"},
        )

    def redeem_key(self, bot: str, key: str) -> dict:
        result = self._do_request(
            "POST",
            f"/api/bot/{bot}/redemption",
            data={"key": key},
        )

        if result.get("error"):
            err = result["error"]
            if self._is_transient(err):
                return {"success": False, "status": "retry", "message": err}
            return {"success": False, "status": "error", "message": err}

        status = result.get("Result") if isinstance(result, dict) else result

        if isinstance(status, str):
            if "Redeem" in status or "redeem" in status:
                return {"success": True, "status": "redeemed", "message": status}
            if "Already" in status or "already" in status:
                return {"success": False, "status": "duplicate", "message": status}
            if "RateLimit" in status or "rate" in status.lower():
                return {"success": False, "status": "retry", "message": status}
            if "Timeout" in status or "throttle" in status.lower():
                return {"success": False, "status": "retry", "message": status}
            if "Invalid" in status:
                return {"success": False, "status": "invalid", "message": status}
            return {"success": True, "status": "submitted", "message": status}

        if isinstance(status, dict):
            result_str = status.get("result", "")
            if result_str in ("Redeemed!", True):
                return {"success": True, "status": "redeemed", "message": status.get("message", "")}
            if "Already" in str(result_str):
                return {"success": False, "status": "duplicate", "message": json.dumps(status)}
            if "Invalid" in str(result_str):
                return {"success": False, "status": "invalid", "message": json.dumps(status)}
            return {
                "success": False,
                "status": "retry" if self._is_transient(str(status)) else "error",
                "message": status.get("message", json.dumps(status)),
            }

        return {"success": False, "status": "error", "message": f"Unexpected response: {str(result)[:200]}"}
