from unittest.mock import patch

import plaid
import pytest

import app as flask_app


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    flask_app.limiter.reset()
    with flask_app.app.test_client() as c:
        yield c


def test_api_summary_returns_200_with_message(client):
    with patch("app.build_summary", return_value="Spent $0\n$0/day avg"):
        resp = client.get("/api/summary")
    assert resp.status_code == 200
    assert resp.is_json
    assert "message" in resp.get_json()


def test_api_summary_plaid_error_returns_502(client):
    with patch("app.build_summary", side_effect=plaid.ApiException(status=400, reason="Bad Request")):
        resp = client.get("/api/summary")
    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_api_summary_missing_tokens_returns_500(client):
    with patch("app.build_summary", side_effect=FileNotFoundError("tokens.json not found")):
        resp = client.get("/api/summary")
    assert resp.status_code == 500
    assert "error" in resp.get_json()
