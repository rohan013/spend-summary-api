import os
from datetime import date

from plaid_client import get_transactions


def compute_budget_status() -> dict:
    today = date.today()
    budget_env = os.getenv("MONTHLY_BUDGET")
    base_budget = float(budget_env) if budget_env else None

    current_month_txns = get_transactions(from_date=date(today.year, today.month, 1))
    month_total = sum(t["amount"] for t in current_month_txns)
    daily_average = month_total / today.day
    top_transactions = sorted(current_month_txns, key=lambda t: t["amount"], reverse=True)[:3]

    if base_budget is not None:
        percent_used = int(month_total / base_budget * 100) if base_budget > 0 else 0
        remaining = base_budget - month_total
    else:
        percent_used = None
        remaining = None

    return {
        "spent": month_total,
        "budget": base_budget,
        "remaining": remaining,
        "percent_used": percent_used,
        "daily_average": daily_average,
        "top_transactions": [{"name": t["name"], "amount": t["amount"]} for t in top_transactions],
    }


def build_summary() -> str:
    status = compute_budget_status()

    if status["budget"] is not None:
        line1 = f"Spent ${status['spent']:,.0f} of ${status['budget']:,.0f} ({status['percent_used']}%)"
        line2 = f"${status['remaining']:,.0f} remaining · ${status['daily_average']:,.0f}/day avg"
    else:
        line1 = f"Spent ${status['spent']:,.0f}"
        line2 = f"${status['daily_average']:,.0f}/day avg"

    message = f"{line1}\n{line2}"
    if status["top_transactions"]:
        line3 = " · ".join(f"{t['name']} ${t['amount']:,.0f}" for t in status["top_transactions"])
        message += f"\n{line3}"
    return message
