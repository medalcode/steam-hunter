import os
from unittest.mock import patch

import pytest
from app.database import FoundCode


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "bots_online" in data
        assert "total_codes" in data


class TestCodes:
    def test_list_codes_empty(self, client):
        resp = client.get("/api/codes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_codes_with_data(self, client, sample_code):
        resp = client.get("/api/codes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["code"] == "ABCDE-12345-FGHIJ"
        assert data[0]["status"] == "new"

    def test_list_codes_filter_by_status(self, client, sample_code, redeemed_code):
        resp = client.get("/api/codes?status=new")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["status"] == "new" for c in data)

    def test_list_codes_filter_by_type(self, client, sample_code, sample_giveaway):
        resp = client.get("/api/codes?code_type=key")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["code_type"] == "key" for c in data)


class TestStats:
    def test_stats_endpoint(self, client, sample_code, redeemed_code):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["new"] == 1
        assert data["redeemed"] == 1

    def test_stats_empty(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestScrape:
    def test_trigger_scrape(self, client, monkeypatch):
        monkeypatch.setattr("app.main.run_scrapers_once", lambda **kw: [])
        resp = client.post("/api/scrape")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestSkip:
    def test_skip_code(self, client, sample_code):
        resp = client.post(f"/api/codes/{sample_code.id}/skip")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Code skipped"

    def test_skip_nonexistent(self, client):
        resp = client.post("/api/codes/99999/skip")
        assert resp.status_code == 404


class TestAuth:
    def test_auth_rejected_when_key_set(self, client, monkeypatch):
        monkeypatch.setattr("app.main._API_KEY_ENV", "test-secret-key")
        resp = client.get("/api/codes")
        assert resp.status_code == 401

    def test_auth_accepted_with_valid_key(self, client, monkeypatch):
        monkeypatch.setattr("app.main._API_KEY_ENV", "test-secret-key")
        resp = client.get("/api/codes", headers={"Authorization": "Bearer test-secret-key"})
        assert resp.status_code == 200

    def test_auth_rejected_with_wrong_key(self, client, monkeypatch):
        monkeypatch.setattr("app.main._API_KEY_ENV", "test-secret-key")
        resp = client.get("/api/codes", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401

    def test_health_excluded_from_auth(self, client, monkeypatch):
        monkeypatch.setattr("app.main._API_KEY_ENV", "test-secret-key")
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_no_auth_when_key_not_set(self, client):
        resp = client.get("/api/codes")
        assert resp.status_code == 200
