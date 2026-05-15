#!/usr/bin/env python3
"""
Terminal Plaid Link flow: opens Plaid Link in the browser, receives the
public_token via a local callback server, exchanges it for an access_token,
then prompts for custom institution/account names and saves to tokens.json.

Usage:
    python setup_accounts.py
"""
import os
import queue
import socket
import sys
import threading
import webbrowser

from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_get_request import ItemGetRequest
from flask import Flask, jsonify, request as flask_request

from plaid_client import create_link_token, exchange_public_token
from token_store import JSONTokenStore

load_dotenv()

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}

_LINK_HTML = """<!DOCTYPE html>
<html>
<head><title>Connect Bank Account</title></head>
<body>
  <h2>Connecting your bank account...</h2>
  <p>If nothing happens, <a href="#" id="open-link">click here</a>.</p>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    const handler = Plaid.create({{
      token: '{link_token}',
      onSuccess: function(public_token, metadata) {{
        fetch('/callback', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{public_token: public_token}})
        }}).then(() => {{
          document.body.innerHTML = '<h2>Success! Return to your terminal.</h2>';
        }});
      }},
      onExit: function(err, metadata) {{
        if (err) {{
          document.body.innerHTML = '<h2>Error: ' + err.display_message + '</h2>';
        }}
      }}
    }});
    handler.open();
    document.getElementById('open-link').onclick = function(e) {{
      e.preventDefault();
      handler.open();
    }};
  </script>
</body>
</html>"""


def _make_client():
    configuration = plaid.Configuration(
        host=_ENV_MAP[os.getenv("PLAID_ENV", "sandbox")],
        api_key={
            "clientId": os.getenv("PLAID_CLIENT_ID"),
            "secret": os.getenv("PLAID_SECRET"),
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


def _prompt(message, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{message}{suffix}: ").strip()
    return raw if raw else default


def _discover(client, access_token):
    item = client.item_get(ItemGetRequest(access_token=access_token))
    institution_id = item["item"]["institution_id"]

    inst = client.institutions_get_by_id(
        InstitutionsGetByIdRequest(
            institution_id=institution_id,
            country_codes=[CountryCode("US")],
        )
    )
    institution_name = inst["institution"]["name"]

    balances = client.accounts_balance_get(
        AccountsBalanceGetRequest(access_token=access_token)
    )
    accounts = [
        {
            "account_id": acct["account_id"],
            "name": acct["name"],
            "type": acct["type"].value,
            "subtype": acct["subtype"].value if acct["subtype"] else "",
        }
        for acct in balances["accounts"]
    ]

    return institution_name, accounts


_store = JSONTokenStore()


def _load():
    try:
        return _store.load_raw()
    except FileNotFoundError:
        return {}


def _save(data):
    _store.save_raw(data)
    print(f"Saved to {_store.path}.")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _run_link_flow() -> str:
    """Launch Plaid Link in the browser and return the exchanged access_token."""
    print("Creating Plaid Link token...")
    link_token = create_link_token()

    token_queue: queue.Queue = queue.Queue()
    app = Flask(__name__)
    log = app.logger
    import logging
    log.setLevel(logging.ERROR)

    html = _LINK_HTML.replace("{link_token}", link_token)

    @app.route("/")
    def link_page():
        return html

    @app.route("/callback", methods=["POST"])
    def callback():
        token_queue.put(flask_request.json["public_token"])
        return jsonify({"status": "ok"})

    port = _free_port()
    threading.Thread(
        target=lambda: app.run(port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()

    url = f"http://localhost:{port}"
    print(f"Opening Plaid Link in your browser...")
    print(f"If the browser doesn't open automatically, visit: {url}")
    webbrowser.open(url)

    print("Waiting for you to complete the Link flow...", flush=True)
    public_token = token_queue.get()

    print("Exchanging token...")
    return exchange_public_token(public_token)


def main():
    client = _make_client()
    config = _load()

    try:
        access_token = _run_link_flow()
    except plaid.ApiException as e:
        print(f"Plaid error: {e.body}")
        sys.exit(1)

    print(f"\n--- Discovering accounts ---")
    try:
        institution_name, accounts = _discover(client, access_token)
    except plaid.ApiException as e:
        print(f"Plaid error: {e.body}")
        sys.exit(1)

    print(f"Institution : {institution_name}")
    print(f"Accounts    : {len(accounts)} found")
    for acct in accounts:
        print(f"  • {acct['name']}  ({acct['type']}/{acct['subtype']})")

    existing_slug = next(
        (s for s, d in config.items() if d.get("access_token") == access_token),
        None,
    )
    default_slug = existing_slug or institution_name.lower().replace(" ", "_")

    print()
    slug = _prompt("Short identifier (internal, e.g. chase)", default_slug)
    existing = config.get(slug, {})
    display_name = _prompt("Display name", existing.get("name", institution_name))

    existing_account_names = existing.get("accounts", {})
    named_accounts = {}
    for acct in accounts:
        aid = acct["account_id"]
        default_name = existing_account_names.get(aid, acct["name"])
        custom = _prompt(f"  Name for '{acct['name']}' ({acct['subtype']})", default_name)
        named_accounts[aid] = custom

    config[slug] = {
        "access_token": access_token,
        "name": display_name,
        "accounts": named_accounts,
    }

    _save(config)
    print(f"\nDone. {len(config)} institution(s) in {_store.path}.")


if __name__ == "__main__":
    main()
