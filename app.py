import os
from datetime import date

from flask import Flask, jsonify
from flask_limiter import Limiter

from plaid_client import get_transactions

app = Flask(__name__)
limiter = Limiter(lambda: "global", app=app, default_limits=["5 per hour"])


@app.route("/api/summary")
def api_summary():
    txns = get_transactions()
    today = date.today()
    month_txns = [
        t for t in txns
        if t["date"].year == today.year and t["date"].month == today.month
    ]
    month_total = sum(t["amount"] for t in month_txns)

    avg_per_day = month_total / today.day

    budget_str = os.getenv("MONTHLY_BUDGET")
    if budget_str:
        budget = float(budget_str)
        pct = int(month_total / budget * 100)
        remaining = budget - month_total
        line1 = f"Spent ${month_total:,.0f} of ${budget:,.0f} ({pct}%)"
        line2 = f"${remaining:,.0f} remaining · ${avg_per_day:,.0f}/day avg"
    else:
        line1 = f"Spent ${month_total:,.0f}"
        line2 = f"${avg_per_day:,.0f}/day avg"

    message = f"{line1}\n{line2}"
    top3 = sorted(month_txns, key=lambda t: t["amount"], reverse=True)[:3]
    if top3:
        line3 = " · ".join(f"{t['name']} ${t['amount']:,.0f}" for t in top3)
        message += f"\n{line3}"

    return jsonify({"message": message})


if __name__ == "__main__":
    app.run(debug=False)
