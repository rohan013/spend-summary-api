import os
from datetime import date

from plaid_client import get_transactions


def build_summary() -> str:
    today = date.today()
    budget_env = os.getenv("MONTHLY_BUDGET")
    base_budget = float(budget_env) if budget_env else None

    all_txns = get_transactions(months_back=2)

    current_month_txns = [
        t for t in all_txns
        if t["date"].year == today.year and t["date"].month == today.month
    ]
    month_total = sum(t["amount"] for t in current_month_txns)
    daily_average = month_total / today.day

    if base_budget is not None:
        percent_used = int(month_total / base_budget * 100) if base_budget > 0 else 0
        remaining = base_budget - month_total
        line1 = f"Spent ${month_total:,.0f} of ${base_budget:,.0f} ({percent_used}%)"
        line2 = f"${remaining:,.0f} remaining · ${daily_average:,.0f}/day avg"
    else:
        line1 = f"Spent ${month_total:,.0f}"
        line2 = f"${daily_average:,.0f}/day avg"

    message = f"{line1}\n{line2}"
    top_transactions = sorted(current_month_txns, key=lambda t: t["amount"], reverse=True)[:3]
    if top_transactions:
        line3 = " · ".join(f"{t['name']} ${t['amount']:,.0f}" for t in top_transactions)
        message += f"\n{line3}"
    return message
