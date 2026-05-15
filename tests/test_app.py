import pytest
from unittest.mock import patch
import app as flask_app


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


_ACCOUNT = {
    "institution": "Chase",
    "name": "Checking",
    "type": "depository",
    "subtype": "checking",
    "current": 1000.0,
    "available": 900.0,
    "currency": "USD",
}


def test_index_returns_200(client):
    with patch("app.get_balances", return_value=[_ACCOUNT]):
        assert client.get("/").status_code == 200


def test_index_renders_account_data(client):
    with patch("app.get_balances", return_value=[_ACCOUNT]):
        html = client.get("/").data.decode()
    assert "Checking" in html
    assert "depository" in html
    assert "1000.00" in html
    assert "900.00" in html
    assert "USD" in html


def test_index_empty_accounts_renders_no_rows(client):
    with patch("app.get_balances", return_value=[]):
        response = client.get("/")
    assert response.status_code == 200
    assert b"<td>" not in response.data


def test_index_null_balances_render_dash(client):
    acct = {**_ACCOUNT, "current": None, "available": None}
    with patch("app.get_balances", return_value=[acct]):
        html = client.get("/").data.decode()
    assert "—" in html
