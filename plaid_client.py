import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from token_store import JSONTokenStore, TokenStore

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
_store = JSONTokenStore()


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


# Excluded primary categories in Plaid's personal_finance_category system
_EXCLUDED_CATEGORIES = {"TRANSFER_IN", "TRANSFER_OUT", "LOAN_PAYMENTS"}


def _format_category(primary: str) -> str:
    return primary.replace("_", " ").title()


def _extract_category(txn) -> str | None:
    """Return display-ready category name, or None if the transaction should be excluded."""
    pfc = txn["personal_finance_category"]
    if pfc:
        primary = pfc["primary"]
        if primary in _EXCLUDED_CATEGORIES:
            return None
        return _format_category(primary)
    # Fall back to legacy category field
    cats = txn["category"] or []
    if not cats:
        return "Uncategorized"
    legacy_excluded = {"Transfer", "Payment", "Credit Card"}
    if cats[0] in legacy_excluded:
        return None
    return cats[0]


def _fetch_institution_transactions(
    access_token: str, start_date: date, end_date: date
) -> list[dict]:
    transactions = []
    offset = 0
    while True:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=500,
                offset=offset,
                include_personal_finance_category=True,
            ),
        )
        response = _client.transactions_get(request)
        batch = response["transactions"]
        transactions.extend(batch)
        if len(transactions) >= response["total_transactions"]:
            break
        offset += len(batch)

    result = []
    for txn in transactions:
        if txn["amount"] <= 0 or txn["pending"]:
            continue
        category = _extract_category(txn)
        if category is None:
            continue
        result.append({
            "amount": txn["amount"],
            "date": txn["date"],
            "category": category,
            "name": txn["name"],
        })
    return result


def get_transactions(store: TokenStore = _store, months_back: int = 5) -> list[dict]:
    institutions = store.list_institutions()
    today = date.today()
    m = today.month - (months_back - 1)
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    start_date = date(y, m, 1)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(_fetch_institution_transactions, inst.access_token, start_date, today)
            for inst in institutions
        ]
        results = [f.result() for f in futures]

    return [txn for batch in results for txn in batch]


