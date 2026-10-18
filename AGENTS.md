# Personal Finance

A Flask app that fetches spending transactions from connected bank accounts via the Plaid API and exposes a single JSON endpoint (`GET /api/summary`) for use by iOS Shortcuts or other clients.

## Tech stack

- Python 3.12
- Flask (web server)
- plaid-python (Plaid API client)
- python-dotenv (env var loading)
- pytest + pytest-cov (testing)

## Running the app

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run          # or: python app.py
# App at http://localhost:5000/api/summary
```

## File map

| File | Role |
|---|---|
| `app.py` | Flask app. Single route `GET /api/summary` calls `get_transactions()` and returns a JSON `{"message": "..."}`. |
| `plaid_client.py` | Plaid API wrapper. Owns `create_link_token`, `exchange_public_token`, and `get_transactions`. Also holds the module-level `_client` (PlaidApi) and `_store` (default JSONTokenStore). |
| `token_store.py` | Persistence layer. `TokenStore` is a `Protocol`; `JSONTokenStore` implements it against `tokens.json`. |
| `models.py` | `InstitutionConfig` dataclass — holds access token, display name, and account ID→name mapping for one institution. |
| `setup_accounts.py` | One-time onboarding script. Runs a local Flask server, opens Plaid Link in the browser, exchanges the public token for an access token, prompts for display names, and saves to `tokens.json`. |
| `tokens.json` | Runtime secret — Plaid access tokens per institution. Not committed. See `tokens.example.json`. |

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
PLAID_CLIENT_ID=...
PLAID_SECRET=...
PLAID_ENV=sandbox   # or: production
```

## Key design decisions

**Dependency injection via `TokenStore` protocol** — `get_transactions(store: TokenStore = _store)` accepts any object with `list_institutions()`. The default `_store` is a module-level `JSONTokenStore()` so `app.py` can call `get_transactions()` with no arguments. Tests inject a mock store directly.

**`plaid_client.py` owns the store** — the token store is Plaid-specific (it holds Plaid access tokens), so it lives alongside the Plaid client rather than being wired up in `app.py`.

**`TokenStore` is a `Protocol`** — storage is intentionally swappable. A SQLite-backed store is the planned next step; no changes to `plaid_client.py` or `app.py` will be needed when that lands.

## Testing

```bash
pytest tests/ --cov=. --cov-branch --cov-report=term-missing --ignore=venv
```

Target: **>85% line and branch coverage** on all application code. Current coverage is 99%.

Tests live in `tests/`. Shared fixtures (e.g. `make_plaid_account`) are in `tests/conftest.py`. The Plaid API client is never called for real in tests — `plaid_client._client` is patched via `patch.object`.

## Planned work

- Migrate storage from `tokens.json` to SQLite. The `TokenStore` protocol means this is a drop-in replacement — add a `SQLiteTokenStore` and swap the default in `plaid_client.py`.
