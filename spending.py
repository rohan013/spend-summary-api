from collections import defaultdict
from datetime import date

AVG_MONTHS = 4

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def compute_spending_summary(
    transactions: list[dict],
    today: date,
    avg_months: int = AVG_MONTHS,
) -> dict:
    monthly: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        d = txn["date"]
        monthly[(d.year, d.month)][txn["category"]] += txn["amount"]

    current_key = (today.year, today.month)
    prior_keys = []
    y, m = today.year, today.month
    for _ in range(avg_months):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        prior_keys.append((y, m))

    current_by_cat = dict(monthly[current_key])
    all_cats: set[str] = set(current_by_cat.keys())
    for key in prior_keys:
        all_cats.update(monthly[key].keys())

    rows = []
    for cat in all_cats:
        current = current_by_cat.get(cat, 0.0)
        avg = sum(monthly[key].get(cat, 0.0) for key in prior_keys) / avg_months
        if current == 0.0 and avg == 0.0:
            continue
        delta = current - avg
        pct = ((delta / avg) * 100) if avg != 0 else None
        rows.append({"name": cat, "current": current, "avg": avg, "delta": delta, "pct": pct})

    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)

    total_current = sum(r["current"] for r in rows)
    total_avg = sum(r["avg"] for r in rows)
    total_delta = total_current - total_avg
    total_pct = ((total_delta / total_avg) * 100) if total_avg != 0 else None

    return {
        "month_label": f"{_MONTH_NAMES[today.month - 1]} {today.year}",
        "avg_months": avg_months,
        "total": {
            "current": total_current,
            "avg": total_avg,
            "delta": total_delta,
            "pct": total_pct,
        },
        "categories": rows,
    }
