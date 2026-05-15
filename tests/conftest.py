from unittest.mock import MagicMock


def make_plaid_account(
    account_id="id1",
    name="Checking",
    type_val="depository",
    subtype_val="checking",
    current=1000.0,
    available=900.0,
    iso_currency="USD",
    unofficial_currency=None,
):
    type_mock = MagicMock()
    type_mock.value = type_val
    subtype_mock = MagicMock() if subtype_val is not None else None
    if subtype_mock is not None:
        subtype_mock.value = subtype_val
    return {
        "account_id": account_id,
        "name": name,
        "type": type_mock,
        "subtype": subtype_mock,
        "balances": {
            "current": current,
            "available": available,
            "iso_currency_code": iso_currency,
            "unofficial_currency_code": unofficial_currency,
        },
    }
