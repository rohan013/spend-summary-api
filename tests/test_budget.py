from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

from budget import build_summary, compute_budget_status


def _txn(amount, year, month, day, name="Store"):
    return {"amount": amount, "date": date(year, month, day), "category": "Food", "name": name}


@contextmanager
def _mock_today(target_date):
    with patch("budget.date") as mock_date:
        mock_date.today.return_value = target_date
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        yield mock_date


# --- build_summary without budget ---


def test_summary_no_budget_empty_transactions():
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=[]), \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        msg = build_summary()
    assert "Spent $0" in msg
    assert "$0/day avg" in msg


def test_summary_no_budget_with_transactions():
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=[_txn(500, 2026, 7, 1)]), \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        msg = build_summary()
    assert "Spent $500" in msg


def test_summary_top_3_transactions():
    txns = [
        _txn(150, 2026, 7, 1, name="Whole Foods"),
        _txn(80, 2026, 7, 2, name="Amazon"),
        _txn(45, 2026, 7, 3, name="Uber"),
    ]
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=txns), \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        msg = build_summary()
    assert "Whole Foods $150" in msg
    assert "Amazon $80" in msg
    assert "Uber $45" in msg


def test_summary_top_transactions_capped_at_3():
    txns = [
        _txn(200, 2026, 7, 1, name="Restaurant"),
        _txn(150, 2026, 7, 2, name="Whole Foods"),
        _txn(80, 2026, 7, 3, name="Amazon"),
        _txn(45, 2026, 7, 4, name="Uber"),
    ]
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=txns), \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        msg = build_summary()
    assert "Uber" not in msg


def test_compute_budget_status_queries_from_first_of_month():
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=[]) as mock_get, \
         patch.dict("os.environ", {"MONTHLY_BUDGET": ""}):
        compute_budget_status()
    mock_get.assert_called_once_with(from_date=date(2026, 7, 1))


# --- build_summary with budget ---


def test_budget_shows_spent_of_total():
    with _mock_today(date(2026, 7, 15)), \
         patch("budget.get_transactions", return_value=[_txn(500, 2026, 7, 1)]), \
         patch.dict("os.environ", {"MONTHLY_BUDGET": "3000"}):
        msg = build_summary()
    assert "of $3,000" in msg
    assert "remaining" in msg
