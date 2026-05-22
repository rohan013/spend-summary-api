from datetime import date
from unittest.mock import patch

import pytest

import app as flask_app


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


def _txn(amount, year, month, day, category="Food and Drink"):
    return {"amount": amount, "date": date(year, month, day), "category": category, "name": "Store"}


def test_api_summary_returns_200_with_message(client):
    with patch("app.get_transactions", return_value=[]):
        resp = client.get("/api/summary")
    assert resp.status_code == 200
    assert resp.is_json
    assert "message" in resp.get_json()


def test_api_summary_message_with_budget(client):
    txns = [_txn(500, 2026, 5, 1)]
    with patch("app.get_transactions", return_value=txns), \
         patch("app.date") as mock_date, \
         patch.dict("os.environ", {"MONTHLY_BUDGET": "3000"}):
        mock_date.today.return_value = date(2026, 5, 15)
        resp = client.get("/api/summary")
    msg = resp.get_json()["message"]
    assert "of $3,000" in msg
    assert "remaining" in msg


def test_api_summary_message_without_budget(client):
    txns = [_txn(500, 2026, 5, 1)]
    with patch("app.get_transactions", return_value=txns), \
         patch("app.date") as mock_date, \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        mock_date.today.return_value = date(2026, 5, 15)
        resp = client.get("/api/summary")
    msg = resp.get_json()["message"]
    assert "Spent $" in msg
    assert "/day avg" in msg
    assert "remaining" not in msg


def test_api_summary_only_counts_current_month(client):
    txns = [
        _txn(100, 2026, 5, 1),  # current month
        _txn(200, 2026, 4, 1),  # prior month — must not be counted
    ]
    with patch("app.get_transactions", return_value=txns), \
         patch("app.date") as mock_date, \
         patch.dict("os.environ", {"MONTHLY_BUDGET": "3000"}):
        mock_date.today.return_value = date(2026, 5, 15)
        resp = client.get("/api/summary")
    msg = resp.get_json()["message"]
    assert "$100" in msg
    assert "$300" not in msg
