from unittest.mock import patch, MagicMock
import json

from app.asf_client import ASFClient


class TestASFClient:
    def setup_method(self):
        self.client = ASFClient("http://localhost:1242", "")

    @patch("app.asf_client.requests.Session.request")
    def test_get_bots_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "Result": {
                "principal": {
                    "BotName": "principal",
                    "IsConnectedAndLoggedOn": True,
                    "CardsFarmer": {"CurrentGamesFarming": [], "GamesToFarm": []},
                },
                "secundaria1": {
                    "BotName": "secundaria1",
                    "IsConnectedAndLoggedOn": False,
                    "CardsFarmer": {"CurrentGamesFarming": [], "GamesToFarm": []},
                },
            },
            "Success": True,
        }
        mock_request.return_value = mock_resp

        bots = self.client.get_bots(["principal", "secundaria1"])
        assert len(bots) == 2
        assert bots[0]["name"] == "principal"
        assert bots[0]["online"] is True
        assert bots[1]["name"] == "secundaria1"
        assert bots[1]["online"] is False

    @patch("app.asf_client.requests.Session.request")
    def test_get_bots_connection_error(self, mock_request):
        from requests.exceptions import ConnectionError
        mock_request.side_effect = ConnectionError()

        bots = self.client.get_bots(["principal"])
        assert bots == []

    @patch("app.asf_client.requests.Session.request")
    def test_redeem_key_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "Result": "Redeem(None)",
            "Success": True,
        }
        mock_request.return_value = mock_resp

        result = self.client.redeem_key("principal", "ABCDE-12345-FGHIJ")
        assert result["success"] is True

    @patch("app.asf_client.requests.Session.request")
    def test_redeem_key_duplicate(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "Result": "Already(None)",
            "Success": True,
        }
        mock_request.return_value = mock_resp

        result = self.client.redeem_key("principal", "ABCDE-12345-FGHIJ")
        assert result["success"] is False
        assert result["status"] == "duplicate"

    @patch("app.asf_client.requests.Session.request")
    def test_redeem_key_403(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.ok = False
        mock_request.return_value = mock_resp

        result = self.client.redeem_key("principal", "ABCDE-12345-FGHIJ")
        assert result["success"] is False
        assert "403" in str(result)

    @patch("app.asf_client.requests.Session.request")
    def test_send_command(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"Result": "OK", "Success": True}
        mock_request.return_value = mock_resp

        result = self.client.send_command("principal", "status")
        assert result.get("Success") is True
