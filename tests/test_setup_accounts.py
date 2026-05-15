import sys
from unittest.mock import MagicMock, patch, call
import plaid
import setup_accounts


# --- _prompt ---

def test_prompt_returns_input_when_non_empty():
    with patch("builtins.input", return_value="chase"):
        assert setup_accounts._prompt("Label") == "chase"


def test_prompt_returns_default_when_input_empty():
    with patch("builtins.input", return_value=""):
        assert setup_accounts._prompt("Label", default="bofa") == "bofa"


def test_prompt_shows_default_in_suffix():
    with patch("builtins.input", return_value="") as mock_input:
        setup_accounts._prompt("Label", default="bofa")
    mock_input.assert_called_once_with("Label [bofa]: ")


def test_prompt_no_suffix_when_no_default():
    with patch("builtins.input", return_value="") as mock_input:
        setup_accounts._prompt("Label")
    mock_input.assert_called_once_with("Label: ")


# --- _discover ---

def _make_discover_client(institution_name="Chase", accounts=None):
    if accounts is None:
        accounts = [{"account_id": "id1", "name": "Checking", "type": MagicMock(value="depository"), "subtype": MagicMock(value="checking")}]
    client = MagicMock()
    client.item_get.return_value = {"item": {"institution_id": "ins_123"}}
    client.institutions_get_by_id.return_value = {"institution": {"name": institution_name}}
    client.accounts_balance_get.return_value = {"accounts": accounts}
    return client


def test_discover_returns_institution_name_and_accounts():
    client = _make_discover_client()
    name, accounts = setup_accounts._discover(client, "access-tok")
    assert name == "Chase"
    assert len(accounts) == 1
    assert accounts[0]["account_id"] == "id1"
    assert accounts[0]["subtype"] == "checking"


def test_discover_subtype_none():
    acct = {"account_id": "id1", "name": "Loan", "type": MagicMock(value="loan"), "subtype": None}
    client = _make_discover_client(accounts=[acct])
    _, accounts = setup_accounts._discover(client, "access-tok")
    assert accounts[0]["subtype"] == ""


# --- _load ---

def test_load_returns_empty_dict_when_file_not_found():
    with patch.object(setup_accounts._store, "load_raw", side_effect=FileNotFoundError):
        assert setup_accounts._load() == {}


def test_load_returns_data_when_file_exists():
    data = {"chase": {"access_token": "tok", "name": "Chase"}}
    with patch.object(setup_accounts._store, "load_raw", return_value=data):
        assert setup_accounts._load() == data


# --- _save ---

def test_save_calls_save_raw_and_prints(capsys):
    with patch.object(setup_accounts._store, "save_raw") as mock_save:
        setup_accounts._save({"chase": {}})
    mock_save.assert_called_once_with({"chase": {}})
    assert str(setup_accounts._store.path) in capsys.readouterr().out


# --- _free_port ---

def test_free_port_returns_valid_port():
    port = setup_accounts._free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535


# --- _make_client ---

def test_make_client_returns_plaid_api_instance():
    from plaid.api import plaid_api
    client = setup_accounts._make_client()
    assert isinstance(client, plaid_api.PlaidApi)


# --- _run_link_flow ---

def test_run_link_flow_returns_access_token():
    mock_q = MagicMock()
    mock_q.get.return_value = "public-token-xyz"

    with patch("setup_accounts.create_link_token", return_value="link-tok"), \
         patch("setup_accounts.exchange_public_token", return_value="access-tok") as mock_exchange, \
         patch("setup_accounts.webbrowser.open"), \
         patch("setup_accounts.queue.Queue", return_value=mock_q), \
         patch("setup_accounts.threading.Thread"):
        result = setup_accounts._run_link_flow()

    assert result == "access-tok"
    mock_exchange.assert_called_once_with("public-token-xyz")


# --- main ---

def _plaid_error(body="plaid error"):
    exc = plaid.ApiException(status=400, reason="Bad Request")
    exc.body = body
    return exc


def test_main_success(capsys):
    accounts = [{"account_id": "id1", "name": "Checking", "official_name": "Chase Checking", "mask": "1234", "type": "depository", "subtype": "checking"}]

    with patch("setup_accounts._make_client"), \
         patch("setup_accounts._load", return_value={}), \
         patch("setup_accounts._run_link_flow", return_value="access-tok"), \
         patch("setup_accounts._discover", return_value=("Chase", accounts)), \
         patch("setup_accounts._save") as mock_save, \
         patch("builtins.input", side_effect=["chase", "Chase Bank", "My Checking"]):
        setup_accounts.main()

    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["chase"]["access_token"] == "access-tok"
    assert saved["chase"]["name"] == "Chase Bank"
    assert saved["chase"]["accounts"] == {"id1": "My Checking"}


def test_main_existing_slug_reused(capsys):
    existing_config = {"chase": {"access_token": "access-tok", "name": "Chase", "accounts": {"id1": "Old Name"}}}
    accounts = [{"account_id": "id1", "name": "Checking", "official_name": "", "mask": "", "type": "depository", "subtype": "checking"}]

    with patch("setup_accounts._make_client"), \
         patch("setup_accounts._load", return_value=existing_config), \
         patch("setup_accounts._run_link_flow", return_value="access-tok"), \
         patch("setup_accounts._discover", return_value=("Chase", accounts)), \
         patch("setup_accounts._save") as mock_save, \
         patch("builtins.input", side_effect=["chase", "Chase Bank", "Updated Name"]):
        setup_accounts.main()

    saved = mock_save.call_args[0][0]
    assert saved["chase"]["accounts"] == {"id1": "Updated Name"}


def test_main_exits_on_link_flow_error():
    import pytest
    with patch("setup_accounts._make_client"), \
         patch("setup_accounts._load", return_value={}), \
         patch("setup_accounts._run_link_flow", side_effect=_plaid_error("link error")):
        with pytest.raises(SystemExit) as exc_info:
            setup_accounts.main()
    assert exc_info.value.code == 1


def test_main_exits_on_discover_error():
    import pytest
    with patch("setup_accounts._make_client"), \
         patch("setup_accounts._load", return_value={}), \
         patch("setup_accounts._run_link_flow", return_value="access-tok"), \
         patch("setup_accounts._discover", side_effect=_plaid_error("discover error")):
        with pytest.raises(SystemExit) as exc_info:
            setup_accounts.main()
    assert exc_info.value.code == 1
