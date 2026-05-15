from unittest.mock import MagicMock, patch
import plaid_client
from models import InstitutionConfig
from tests.conftest import make_plaid_account


def _institution(access_token="tok", name="Chase", accounts=None):
    return InstitutionConfig(access_token=access_token, name=name, accounts=accounts or {})


# --- create_link_token ---

def test_create_link_token():
    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.link_token_create.return_value = {"link_token": "link-sandbox-abc"}
        assert plaid_client.create_link_token() == "link-sandbox-abc"


# --- exchange_public_token ---

def test_exchange_public_token():
    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.item_public_token_exchange.return_value = {"access_token": "access-sandbox-xyz"}
        assert plaid_client.exchange_public_token("public-token-123") == "access-sandbox-xyz"


# --- get_balances ---

def test_get_balances_empty_store():
    store = MagicMock()
    store.list_institutions.return_value = []
    assert plaid_client.get_balances(store) == []


def test_get_balances_basic_account():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    acct = make_plaid_account()

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [acct]}
        result = plaid_client.get_balances(store)

    assert len(result) == 1
    row = result[0]
    assert row["institution"] == "Chase"
    assert row["name"] == "Checking"
    assert row["type"] == "depository"
    assert row["subtype"] == "checking"
    assert row["current"] == 1000.0
    assert row["available"] == 900.0
    assert row["currency"] == "USD"


def test_get_balances_custom_account_name():
    store = MagicMock()
    store.list_institutions.return_value = [_institution(accounts={"id1": "My Checking"})]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [make_plaid_account(account_id="id1")]}
        result = plaid_client.get_balances(store)

    assert result[0]["name"] == "My Checking"


def test_get_balances_falls_back_to_plaid_name_when_no_mapping():
    store = MagicMock()
    store.list_institutions.return_value = [_institution(accounts={})]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [make_plaid_account(account_id="id1", name="Plaid Name")]}
        result = plaid_client.get_balances(store)

    assert result[0]["name"] == "Plaid Name"


def test_get_balances_subtype_none():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [make_plaid_account(subtype_val=None)]}
        result = plaid_client.get_balances(store)

    assert result[0]["subtype"] == ""


def test_get_balances_unofficial_currency():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [make_plaid_account(iso_currency=None, unofficial_currency="BTC")]}
        result = plaid_client.get_balances(store)

    assert result[0]["currency"] == "BTC"


def test_get_balances_multiple_institutions():
    store = MagicMock()
    store.list_institutions.return_value = [
        _institution(access_token="tok1", name="Chase"),
        _institution(access_token="tok2", name="BofA"),
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.side_effect = [
            {"accounts": [make_plaid_account(name="Savings")]},
            {"accounts": [make_plaid_account(name="Checking")]},
        ]
        result = plaid_client.get_balances(store)

    assert len(result) == 2
    assert result[0]["institution"] == "Chase"
    assert result[1]["institution"] == "BofA"


def test_get_balances_multiple_accounts_one_institution():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.accounts_balance_get.return_value = {"accounts": [
            make_plaid_account(account_id="id1", name="Checking"),
            make_plaid_account(account_id="id2", name="Savings"),
        ]}
        result = plaid_client.get_balances(store)

    assert len(result) == 2


# --- get_transactions ---

from datetime import date as _date


def _make_txn(amount=50.0, year=2026, month=5, day=1, pfc_primary="FOOD_AND_DRINK", pending=False, name="Store"):
    return {
        "amount": amount,
        "date": _date(year, month, day),
        "personal_finance_category": {"primary": pfc_primary},
        "category": None,
        "name": name,
        "pending": pending,
    }


def test_get_transactions_empty_store():
    store = MagicMock()
    store.list_institutions.return_value = []
    assert plaid_client.get_transactions(store) == []


def test_get_transactions_basic_shape():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txn = _make_txn()

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": [txn],
            "total_transactions": 1,
        }
        result = plaid_client.get_transactions(store)

    assert len(result) == 1
    assert result[0]["amount"] == 50.0
    assert result[0]["category"] == "Food And Drink"
    assert result[0]["name"] == "Store"
    assert result[0]["date"] == _date(2026, 5, 1)


def test_get_transactions_filters_excluded_pfc_categories():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txns = [
        _make_txn(pfc_primary="TRANSFER_IN"),
        _make_txn(pfc_primary="TRANSFER_OUT"),
        _make_txn(pfc_primary="LOAN_PAYMENTS"),
        _make_txn(pfc_primary="FOOD_AND_DRINK"),
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": txns,
            "total_transactions": len(txns),
        }
        result = plaid_client.get_transactions(store)

    assert len(result) == 1
    assert result[0]["category"] == "Food And Drink"


def test_get_transactions_filters_nonpositive_amounts():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txns = [
        _make_txn(amount=-10.0),
        _make_txn(amount=0.0),
        _make_txn(amount=25.0),
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": txns,
            "total_transactions": len(txns),
        }
        result = plaid_client.get_transactions(store)

    assert len(result) == 1
    assert result[0]["amount"] == 25.0


def test_get_transactions_filters_pending():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txns = [_make_txn(pending=True), _make_txn(pending=False)]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": txns,
            "total_transactions": len(txns),
        }
        result = plaid_client.get_transactions(store)

    assert len(result) == 1


def test_get_transactions_falls_back_to_legacy_category():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txn = {**_make_txn(), "personal_finance_category": None, "category": ["Food and Drink"]}

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": [txn],
            "total_transactions": 1,
        }
        result = plaid_client.get_transactions(store)

    assert result[0]["category"] == "Food and Drink"


def test_get_transactions_legacy_fallback_no_category_returns_uncategorized():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txn = {**_make_txn(), "personal_finance_category": None, "category": None}

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": [txn],
            "total_transactions": 1,
        }
        result = plaid_client.get_transactions(store)

    assert result[0]["category"] == "Uncategorized"


def test_get_transactions_legacy_excluded_categories_filtered():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    txns = [
        {**_make_txn(), "personal_finance_category": None, "category": ["Transfer"]},
        {**_make_txn(), "personal_finance_category": None, "category": ["Food and Drink"]},
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.return_value = {
            "transactions": txns,
            "total_transactions": len(txns),
        }
        result = plaid_client.get_transactions(store)

    assert len(result) == 1


def test_get_transactions_paginates():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]
    page1 = [_make_txn(amount=10.0)] * 2
    page2 = [_make_txn(amount=20.0)]

    responses = [
        {"transactions": page1, "total_transactions": 3},
        {"transactions": page2, "total_transactions": 3},
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.side_effect = responses
        result = plaid_client.get_transactions(store)

    assert len(result) == 3
    assert mock_client.transactions_get.call_count == 2


def test_get_transactions_year_rollover_start_date():
    store = MagicMock()
    store.list_institutions.return_value = [_institution()]

    with patch.object(plaid_client, "_client") as mock_client, \
         patch("plaid_client.date") as mock_date:
        mock_date.today.return_value = _date(2026, 1, 15)
        mock_date.side_effect = lambda *a: _date(*a)
        mock_client.transactions_get.return_value = {
            "transactions": [],
            "total_transactions": 0,
        }
        plaid_client.get_transactions(store, months_back=5)

    req = mock_client.transactions_get.call_args[0][0]
    # months_back=5 → start_date should be Sep 1, 2025 (Jan - 4 months)
    assert req["start_date"] == _date(2025, 9, 1)


def test_get_transactions_multiple_institutions_merged():
    store = MagicMock()
    store.list_institutions.return_value = [
        _institution(access_token="tok1", name="Chase"),
        _institution(access_token="tok2", name="BofA"),
    ]

    with patch.object(plaid_client, "_client") as mock_client:
        mock_client.transactions_get.side_effect = [
            {"transactions": [_make_txn(amount=100.0)], "total_transactions": 1},
            {"transactions": [_make_txn(amount=200.0)], "total_transactions": 1},
        ]
        result = plaid_client.get_transactions(store)

    assert len(result) == 2
    amounts = {r["amount"] for r in result}
    assert amounts == {100.0, 200.0}
