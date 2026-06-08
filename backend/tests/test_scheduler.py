from unittest.mock import patch, MagicMock
import json
import time

from app.scheduler import _should_skip_scraper, _record_scraper_failure, _record_scraper_success, _get_free_sub, SCRAPER_BACKOFF_MINUTES


class TestScraperBackoff:
    def teardown_method(self):
        from app.scheduler import _scraper_cooldowns
        _scraper_cooldowns.clear()

    def test_no_cooldown_initially(self):
        assert _should_skip_scraper("test_source") is False

    def test_skip_after_failure(self):
        _record_scraper_failure("test_source")
        assert _should_skip_scraper("test_source") is True

    def test_dont_skip_after_success(self):
        _record_scraper_failure("test_source")
        _record_scraper_success("test_source")
        assert _should_skip_scraper("test_source") is False

    def test_multiple_sources_independent(self):
        _record_scraper_failure("source_a")
        _record_scraper_success("source_b")
        assert _should_skip_scraper("source_a") is True
        assert _should_skip_scraper("source_b") is False


class TestGetFreeSub:
    @patch("app.scheduler.http_requests.get")
    def test_free_sub_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "12345": {
                "data": {
                    "is_free": True,
                    "package_groups": [
                        {
                            "subs": [
                                {"packageid": 67890, "price": {"initial": 0}}
                            ]
                        }
                    ],
                }
            }
        }
        mock_get.return_value = mock_resp

        result = _get_free_sub("12345")
        assert result == "67890"

    @patch("app.scheduler.http_requests.get")
    def test_not_free(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "12345": {
                "data": {
                    "is_free": False,
                    "package_groups": [],
                }
            }
        }
        mock_get.return_value = mock_resp

        result = _get_free_sub("12345")
        assert result is None

    @patch("app.scheduler.http_requests.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = _get_free_sub("12345")
        assert result is None

    @patch("app.scheduler.http_requests.get")
    def test_no_price_zero_subs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "12345": {
                "data": {
                    "is_free": True,
                    "package_groups": [
                        {
                            "subs": [
                                {"packageid": 67890, "price": {"initial": 999}}
                            ]
                        }
                    ],
                }
            }
        }
        mock_get.return_value = mock_resp

        result = _get_free_sub("12345")
        assert result is None
