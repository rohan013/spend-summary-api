import os
from datetime import date

from flask import Flask, jsonify

from plaid_client import get_transactions

app = Flask(__name__)


@app.route("/api/summary")
def api_summary():
    txns = get_transactions()
    today = date.today()
    month_total = sum(
        t["amount"] for t in txns
        if t["date"].year == today.year and t["date"].month == today.month
    )

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

    return jsonify({"message": f"{line1}\n{line2}"})


if __name__ == "__main__":
    app.run(debug=True)
