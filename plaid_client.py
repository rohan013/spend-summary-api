import os

from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

from token_store import TokenStore

load_dotenv()

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}

_configuration = plaid.Configuration(
    host=_ENV_MAP[os.getenv("PLAID_ENV", "sandbox")],
    api_key={
        "clientId": os.getenv("PLAID_CLIENT_ID"),
        "secret": os.getenv("PLAID_SECRET"),
    },
)
_client = plaid_api.PlaidApi(plaid.ApiClient(_configuration))


def create_link_token() -> str:
    response = _client.link_token_create(LinkTokenCreateRequest(
        client_name="Personal Finance",
        user=LinkTokenCreateRequestUser(client_user_id="local-user"),
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    ))
    return response["link_token"]


def exchange_public_token(public_token: str) -> str:
    response = _client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    return response["access_token"]


def get_balances(store: TokenStore) -> list[dict]:
    accounts = []

    for institution in store.list_institutions():
        response = _client.accounts_balance_get(
            AccountsBalanceGetRequest(access_token=institution.access_token)
        )
        for acct in response["accounts"]:
            bal = acct["balances"]
            accounts.append({
                "institution": institution.name,
                "name": institution.accounts.get(acct["account_id"], acct["name"]),
                "type": acct["type"].value,
                "subtype": acct["subtype"].value if acct["subtype"] else "",
                "current": bal["current"],
                "available": bal["available"],
                "currency": bal["iso_currency_code"] or bal["unofficial_currency_code"],
            })

    return accounts
