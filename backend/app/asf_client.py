import logging
import requests
import json

logger = logging.getLogger(__name__)

ASF_IPC_DEFAULT = "http://localhost:1243"

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

    def _extract_bot_data(self, result: dict | None, bot_name: str) -> dict | None:
        if not isinstance(result, dict) or "Result" not in result:
            return None
        inner = result["Result"]
        if isinstance(inner, dict) and bot_name in inner:
            return inner[bot_name]
        if isinstance(inner, dict) and "BotName" in inner:
            return inner
        return None

    def get_bots(self, known_bots: list[str] | None = None) -> list[dict]:
        known_bots = known_bots or ["principal", "secundaria1"]
        bots = []
        for bot_name in known_bots:
            result = self._do_request("GET", f"/api/bot/{bot_name}")
            b = self._extract_bot_data(result, bot_name)
            if b:
                bots.append({
                    "name": b.get("BotName", bot_name),
                    "status": b.get("Status", "?"),
                    "online": b.get("IsConnectedAndLoggedOn", False),
                    "games": len(b.get("CardsFarmer", {}).get("CurrentGamesFarming", [])),
                })
        return bots

    def get_bot_status(self, bot: str) -> dict:
        result = self._do_request("GET", f"/api/bot/{bot}")
        b = self._extract_bot_data(result, bot)
        if b:
            return {
                "name": b.get("BotName", bot),
                "status": b.get("Status", "?"),
                "online": b.get("IsConnectedAndLoggedOn", False),
            }
        return {}

    def redeem_key(self, bot: str, key: str) -> dict:
        result = self._do_request(
            "POST",
            f"/api/bot/{bot}/redemption",
            data={"key": key},
        )

        status = result.get("Result") if isinstance(result, dict) else result

        if isinstance(status, str):
            if "Redeem" in status or "redeem" in status:
                return {"success": True, "status": status, "message": status}
            if "Already" in status or "already" in status:
                return {"success": False, "status": "duplicate", "message": status}
            return {"success": True, "status": "submitted", "message": status}

        if isinstance(status, dict):
            return {
                "success": status.get("result") in ("Redeemed!", True),
                "status": status.get("result", "unknown"),
                "message": status.get("message", json.dumps(status)),
            }

        if isinstance(result, dict):
            error = result.get("error") or result.get("Message", "")
            if error:
                return {"success": False, "status": "error", "message": error}

        return {"success": True, "status": "submitted", "message": str(result)[:200]}

    def send_command(self, bot: str, command: str) -> dict:
        return self._do_request(
            "POST",
            "/api/command",
            data={"command": f"{command} {bot}"},
        )
