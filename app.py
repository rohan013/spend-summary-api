import plaid
from flask import Flask, jsonify
from flask_limiter import Limiter

from budget import build_summary

app = Flask(__name__)
limiter = Limiter(lambda: "global", app=app, default_limits=["5 per hour"])


@app.route("/api/summary")
def api_summary():
    try:
        return jsonify({"message": build_summary()})
    except plaid.ApiException:
        return jsonify({"error": "Failed to fetch transactions from Plaid"}), 502
    except FileNotFoundError:
        return jsonify({"error": "No linked accounts found — run setup_accounts.py first"}), 500


if __name__ == "__main__":
    app.run(debug=False)
