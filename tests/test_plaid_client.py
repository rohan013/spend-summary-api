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
