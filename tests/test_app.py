from datetime import date
from unittest.mock import patch

import pytest

import app as flask_app


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c

_SUMMARY = {
    "month_label": "May 2026",
    "avg_months": 4,
    "total": {"current": 500.0, "avg": 400.0, "delta": 100.0, "pct": 25.0},
    "categories": [
        {"name": "Food and Drink", "current": 300.0, "avg": 200.0, "delta": 100.0, "pct": 50.0,
         "top_txns": [{"name": "Whole Foods", "amount": 89.50}]},
    ],
}

_EMPTY_SUMMARY = {
    "month_label": "May 2026",
    "avg_months": 4,
    "total": {"current": 0.0, "avg": 0.0, "delta": 0.0, "pct": None},
    "categories": [],
}


def test_index_returns_200(client):
    with patch("app.get_transactions", return_value=[]), \
         patch("app.compute_spending_summary", return_value=_SUMMARY):
        assert client.get("/").status_code == 200


def test_index_renders_month_label(client):
    with patch("app.get_transactions", return_value=[]), \
         patch("app.compute_spending_summary", return_value=_SUMMARY):
        html = client.get("/").data.decode()
    assert "May 2026" in html


def test_index_renders_category_row(client):
    with patch("app.get_transactions", return_value=[]), \
         patch("app.compute_spending_summary", return_value=_SUMMARY):
        html = client.get("/").data.decode()
    assert "Food and Drink" in html
    assert "300.00" in html


def test_index_empty_summary_renders_hero_without_categories(client):
    with patch("app.get_transactions", return_value=[]), \
         patch("app.compute_spending_summary", return_value=_EMPTY_SUMMARY):
        html = client.get("/").data.decode()
    assert "Monthly Spending" in html
    assert "Food and Drink" not in html
