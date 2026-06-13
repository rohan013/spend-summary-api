# Personal Finance

A Flask app that pulls spending transactions from connected bank accounts via the Plaid API and exposes a single JSON endpoint — `GET /api/summary` — for use by an iOS Shortcut or any other HTTP client.

This repo is designed to be **forked and self-hosted**: each deployment uses its own Plaid app credentials and its own `tokens.json` of linked accounts. There's no multi-user support — it's one instance per person/household.

---

## How it works — end to end

```
Client (e.g. iOS Shortcut)
    │  HTTPS request to your domain
    ▼
Your reverse proxy / tunnel (your choice — see "Deploying" below)
    ▼
Flask app: GET /api/summary  (gunicorn, via systemd or Docker)
    │  Fetches settled, non-transfer transactions for all linked
    │  institutions in parallel
    ▼
Plaid API
    │
    ▼
JSON response  →  back up the chain  →  client displays it
```

---

## Components

### 1. Flask app (`app.py`)

One route: `GET /api/summary`

- Calls `get_transactions()` to fetch all settled, non-transfer transactions for the current month.
- Sums them up and computes a daily average.
- If `MONTHLY_BUDGET` is set in `.env`, also shows budget percentage and remaining amount.
- Returns a single JSON object: `{"message": "Spent $X of $Y (Z%)\n$R remaining · $A/day avg"}`
- On error, returns a JSON `{"error": "..."}` — see [API responses](#api-responses).

Rate limited to **5 requests per hour** globally (in-memory, resets on restart).

### 2. Plaid client (`plaid_client.py`)

- Reads `PLAID_CLIENT_ID`, `PLAID_SECRET`, and `PLAID_ENV` from `.env` at import time.
- `get_transactions(store, months_back=5)` — fetches transactions from all linked institutions **in parallel** using `ThreadPoolExecutor`. Returns only settled (non-pending), non-transfer, positive-amount transactions.
- Excluded Plaid categories: `TRANSFER_IN`, `TRANSFER_OUT`, `LOAN_PAYMENTS` (avoids double-counting money moved between accounts).
- Pagination is handled automatically — loops until all transactions are fetched (Plaid caps at 500 per request).

### 3. Token store (`token_store.py`)

- `TokenStore` is a Protocol (structural interface) — any object with `list_institutions()` satisfies it.
- `JSONTokenStore` is the default implementation, backed by `tokens.json`.
- `tokens.json` holds one entry per bank, each with a Plaid `access_token`, a display name, and optional account ID → custom name mappings.
- This is the only file that holds real credentials — **never commit it**.

### 4. Institution setup (`setup_accounts.py`)

One-time script to connect a new bank account. Run this interactively:

```bash
source venv/bin/activate
python setup_accounts.py
```

What it does:
1. Creates a Plaid Link token via the API.
2. Spins up a temporary local Flask server on a random port.
3. Opens Plaid Link in your browser — you log in to your bank through Plaid's UI.
4. Plaid sends a `public_token` back to the local callback server.
5. The script exchanges the `public_token` for a permanent `access_token`.
6. Discovers all accounts under that institution and lets you give them custom names.
7. Saves everything to `tokens.json`.

Run it once per bank. Re-run it on an existing institution to rename accounts or refresh the token.

### 5. `models.py`

Single dataclass `InstitutionConfig` — holds `access_token`, `name`, and an `accounts` dict (account ID → display name). This is what `JSONTokenStore.list_institutions()` returns.

---

## File map

| File | Role |
|---|---|
| `app.py` | Flask app. Single route `GET /api/summary`. |
| `plaid_client.py` | Plaid API wrapper. Fetches transactions, handles pagination and parallel institution fetching. |
| `token_store.py` | Storage layer. `TokenStore` protocol + `JSONTokenStore` implementation. |
| `models.py` | `InstitutionConfig` dataclass. |
| `setup_accounts.py` | One-time onboarding script to connect a bank account via Plaid Link. |
| `tokens.json` | Runtime secret — Plaid access tokens. **Never commit.** |
| `tokens.example.json` | Safe example showing the `tokens.json` structure. |
| `deploy.sh` | Installs dependencies, writes the systemd unit, enables and starts the service. |
| `undeploy.sh` | Stops and removes the systemd unit. Leaves `.env` and `venv` intact. |
| `Dockerfile` / `.dockerignore` | Container image for running the app without systemd. |
| `LICENSE` | MIT license. |

---

## Environment variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `PLAID_CLIENT_ID` | Yes | Plaid dashboard → Team Settings → Keys |
| `PLAID_SECRET` | Yes | Plaid dashboard → use the key matching `PLAID_ENV` |
| `PLAID_ENV` | Yes | `sandbox` or `production` |
| `MONTHLY_BUDGET` | No | Budget ceiling in dollars (e.g. `3500`). Enables % and remaining in the summary. |

---

## Using this for yourself

1. Fork or clone this repo.
2. Create a [Plaid](https://plaid.com) account and app to get your `PLAID_CLIENT_ID` and `PLAID_SECRET`.
3. `cp .env.example .env` and fill in your Plaid credentials.
4. Link your bank accounts:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python setup_accounts.py
   ```
   This opens Plaid Link in your browser and saves access tokens to `tokens.json` (never commit this file).
5. Deploy using one of the options below.

---

## Running locally (dev)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run          # or: python app.py
# App at http://localhost:5000/api/summary
```

## Deploying

### Option A: systemd (`deploy.sh`)

```bash
./deploy.sh        # installs deps, writes systemd unit, starts service
./undeploy.sh      # stops and removes systemd unit
```

Requires a systemd-based Linux host. This runs gunicorn on `0.0.0.0:8317` as a systemd service with auto-restart on failure and sandboxing (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`, with `ReadWritePaths` scoped to the repo so `tokens.json` stays writable).

```bash
sudo systemctl status personal-finance
sudo systemctl restart personal-finance
sudo journalctl -u personal-finance -f        # live logs
```

This does **not** expose the app to the internet on its own — you're responsible for routing traffic to it (reverse proxy, tunnel, VPN, etc.). See the example recipe below.

### Option B: Docker

```bash
docker build -t personal-finance .
docker run -d \
  --name personal-finance \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/tokens.json:/app/tokens.json \
  personal-finance
```

Set `PORT` (default `8000`) in `.env` to change the port gunicorn binds to inside the container. As with the systemd option, this only binds locally/in-container — put it behind whatever reverse proxy or tunnel you prefer.

### Example deployment recipe: Oracle Cloud VM + Cloudflare Tunnel

This is one way to get a `deploy.sh`-managed instance reachable from the internet with **no open inbound ports** — the setup this repo was originally built for.

```
iOS Shortcut
    │  HTTPS request to your-finance.example.com
    │  Headers: CF-Access-Client-Id + CF-Access-Client-Secret
    ▼
Cloudflare Edge (your-finance.example.com)
    │  TLS termination, DDoS protection
    │  Cloudflare Access checks service token → allow
    ▼
cloudflared tunnel (running on the VM)
    │  Encrypted tunnel from Cloudflare edge to the VM
    │  No open inbound ports required on the VM
    ▼
localhost:8317 (gunicorn, 2 workers, via deploy.sh)
```

The Oracle Cloud free-tier VM is **not** exposed directly to the internet — there are no open inbound firewall ports for the app.

#### Cloudflare Tunnel (`cloudflared` systemd service)

`cloudflared` runs as a systemd service and maintains an outbound-only encrypted tunnel to Cloudflare's edge. Because the connection is initiated from the VM, **no inbound port needs to be opened** on the host firewall.

The tunnel is token-based (remotely managed). Ingress routing (`your-finance.example.com` → `http://localhost:8317`) is configured in the Cloudflare Zero Trust dashboard under:
**Networks → Connectors → Cloudflare Tunnels → your tunnel → Edit → Published application routes**

```
/etc/systemd/system/cloudflared.service
ExecStart: cloudflared --no-autoupdate tunnel run --token <token>
```

Manage it with:
```bash
sudo systemctl status cloudflared
sudo systemctl restart cloudflared
```

#### Cloudflare Access (authentication gate)

The domain is protected by a Cloudflare Access policy — unauthenticated requests get a 403. Access is granted via a **service token** (for the iOS Shortcut and machine clients):

| Header | Where to find it |
|---|---|
| `CF-Access-Client-Id` | Cloudflare Zero Trust → Access → Service Tokens |
| `CF-Access-Client-Secret` | Cloudflare Zero Trust → Access → Service Tokens (shown once on creation) |

Human users can be granted access via the Access policy in the Cloudflare Zero Trust dashboard (**Access → Applications**).

---

## API responses

`GET /api/summary` returns one of:

| Status | Body | When |
|---|---|---|
| 200 | `{"message": "Spent $X of $Y (Z%)\n$R remaining · $A/day avg\n..."}` | Success |
| 502 | `{"error": "Failed to fetch transactions from Plaid"}` | Plaid API call failed (e.g. expired/revoked item) |
| 500 | `{"error": "No linked accounts found — run setup_accounts.py first"}` | `tokens.json` doesn't exist yet |

---

## Testing

```bash
pytest tests/ --cov=. --cov-branch --cov-report=term-missing --ignore=venv
```

Target: >85% line and branch coverage. The Plaid API is never called in tests — `plaid_client._client` is patched via `patch.object`.

A GitHub Actions workflow (`.github/workflows/test.yml`) runs this suite on every push and PR, failing if coverage drops below 85%.
