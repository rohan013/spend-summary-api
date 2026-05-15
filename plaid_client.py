import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

load_dotenv()

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "development": plaid.Environment.Development,
    "production": plaid.Environment.Production,
}

_configuration = plaid.Configuration(
    host=_ENV_MAP[os.getenv("PLAID_ENV", "development")],
    api_key={
        "clientId": os.getenv("PLAID_CLIENT_ID"),
        "secret": os.getenv("PLAID_SECRET"),
    },
)
_client = plaid_api.PlaidApi(plaid.ApiClient(_configuration))


def get_balances() -> list[dict]:
    access_token = os.getenv("PLAID_ACCESS_TOKEN")
    response = _client.accounts_balance_get(
        AccountsBalanceGetRequest(access_token=access_token)
    )
    accounts = []
    for acct in response["accounts"]:
        bal = acct["balances"]
        accounts.append({
            "name": acct["name"],
            "type": acct["type"].value,
            "subtype": acct["subtype"].value if acct["subtype"] else "",
            "current": bal["current"],
            "available": bal["available"],
            "currency": bal["iso_currency_code"] or bal["unofficial_currency_code"],
        })
    return accounts
