# Personal Finance

A minimal Flask web app that displays account balances from your linked bank accounts via the [Plaid API](https://plaid.com/docs/).

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example env file and fill in your Plaid credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `PLAID_CLIENT_ID` | Found in your Plaid dashboard |
| `PLAID_SECRET` | Found in your Plaid dashboard (use the key matching your environment) |
| `PLAID_ENV` | `sandbox`, `development`, or `production` |
| `PLAID_ACCESS_TOKEN` | Access token for your linked bank account |

### 3. Run

```bash
python app.py
```

Open http://localhost:5000 to see your account balances.

## Project Structure

```
├── app.py            # Flask routes
├── plaid_client.py   # Plaid API client and balance fetching
├── templates/
│   └── index.html    # Balance table
├── .env.example      # Credential template (safe to commit)
└── requirements.txt
```
