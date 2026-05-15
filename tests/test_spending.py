from datetime import date

import pytest

from spending import compute_spending_summary


def _txn(amount, year, month, day, category="Food and Drink"):
    return {"amount": amount, "date": date(year, month, day), "category": category, "name": "Store"}


TODAY = date(2026, 5, 15)


def test_basic_delta_and_pct():
    txns = [
        # Current month (May): $300
        _txn(300, 2026, 5, 1),
        # Prior 4 months: Jan $100, Feb $100, Mar $100, Apr $100 → avg $100
        _txn(100, 2026, 1, 1),
        _txn(100, 2026, 2, 1),
        _txn(100, 2026, 3, 1),
        _txn(100, 2026, 4, 1),
    ]
    result = compute_spending_summary(txns, TODAY)
    cat = result["categories"][0]
    assert cat["current"] == pytest.approx(300.0)
    assert cat["avg"] == pytest.approx(100.0)
    assert cat["delta"] == pytest.approx(200.0)
    assert cat["pct"] == pytest.approx(200.0)


def test_total_aggregates_categories():
    txns = [
        _txn(200, 2026, 5, 1, "Food and Drink"),
        _txn(100, 2026, 5, 1, "Travel"),
        _txn(50, 2026, 1, 1, "Food and Drink"),
        _txn(50, 2026, 1, 1, "Travel"),
        _txn(50, 2026, 2, 1, "Food and Drink"),
        _txn(50, 2026, 2, 1, "Travel"),
        _txn(50, 2026, 3, 1, "Food and Drink"),
        _txn(50, 2026, 3, 1, "Travel"),
        _txn(50, 2026, 4, 1, "Food and Drink"),
        _txn(50, 2026, 4, 1, "Travel"),
    ]
    result = compute_spending_summary(txns, TODAY)
    # avg per category = 200/4 = 50
    assert result["total"]["current"] == pytest.approx(300.0)
    assert result["total"]["avg"] == pytest.approx(100.0)
    assert result["total"]["delta"] == pytest.approx(200.0)


def test_new_category_has_none_pct():
    txns = [_txn(100, 2026, 5, 1)]
    result = compute_spending_summary(txns, TODAY)
    cat = result["categories"][0]
    assert cat["avg"] == pytest.approx(0.0)
    assert cat["pct"] is None


def test_category_absent_this_month():
    txns = [
        _txn(100, 2026, 1, 1),
        _txn(100, 2026, 2, 1),
        _txn(100, 2026, 3, 1),
        _txn(100, 2026, 4, 1),
    ]
    result = compute_spending_summary(txns, TODAY)
    cat = result["categories"][0]
    assert cat["current"] == pytest.approx(0.0)
    assert cat["avg"] == pytest.approx(100.0)
    assert cat["delta"] == pytest.approx(-100.0)


def test_zero_zero_categories_dropped():
    txns = []
    result = compute_spending_summary(txns, TODAY)
    assert result["categories"] == []
    assert result["total"]["current"] == pytest.approx(0.0)


def test_categories_sorted_by_abs_delta():
    txns = [
        # Food: current=$50, avg=$50 → delta=0
        _txn(50, 2026, 5, 1, "Food and Drink"),
        _txn(50, 2026, 1, 1, "Food and Drink"),
        _txn(50, 2026, 2, 1, "Food and Drink"),
        _txn(50, 2026, 3, 1, "Food and Drink"),
        _txn(50, 2026, 4, 1, "Food and Drink"),
        # Travel: current=$200, avg=$0 → delta=200
        _txn(200, 2026, 5, 1, "Travel"),
    ]
    result = compute_spending_summary(txns, TODAY)
    names = [c["name"] for c in result["categories"]]
    assert names[0] == "Travel"


def test_month_label():
    result = compute_spending_summary([], TODAY)
    assert result["month_label"] == "May 2026"


def test_avg_months_reflected_in_output():
    result = compute_spending_summary([], TODAY, avg_months=3)
    assert result["avg_months"] == 3


def test_missing_month_still_divides_by_avg_months():
    # Category only appears in 2 of 4 prior months; avg should still be divided by 4
    txns = [
        _txn(100, 2026, 1, 1),
        _txn(100, 2026, 2, 1),
        # March and April: absent
    ]
    result = compute_spending_summary(txns, TODAY)
    cat = result["categories"][0]
    assert cat["avg"] == pytest.approx(50.0)  # 200 / 4


def test_total_pct_none_when_avg_is_zero():
    txns = [_txn(100, 2026, 5, 1)]
    result = compute_spending_summary(txns, TODAY)
    assert result["total"]["pct"] is None


def test_year_rollover_in_prior_months():
    # today=Jan 2026; prior 4 months cross into 2025 (Oct, Nov, Dec 2025, and then... wait)
    # Jan 2026: prior = Dec/Nov/Oct/Sep 2025
    jan_today = date(2026, 1, 15)
    txns = [
        _txn(100, 2025, 10, 1),
        _txn(100, 2025, 11, 1),
        _txn(100, 2025, 12, 1),
        _txn(100, 2026, 1, 1),
    ]
    result = compute_spending_summary(txns, jan_today)
    # Sep 2025 missing (no txns), Oct/Nov/Dec each $100 → avg = 300/4 = 75
    cat = result["categories"][0]
    assert cat["avg"] == pytest.approx(75.0)
    assert cat["current"] == pytest.approx(100.0)


def test_under_spending_negative_delta():
    txns = [
        _txn(50, 2026, 5, 1),
        _txn(200, 2026, 1, 1),
        _txn(200, 2026, 2, 1),
        _txn(200, 2026, 3, 1),
        _txn(200, 2026, 4, 1),
    ]
    result = compute_spending_summary(txns, TODAY)
    cat = result["categories"][0]
    assert cat["delta"] < 0
    assert cat["pct"] < 0
