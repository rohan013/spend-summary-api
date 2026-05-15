from datetime import date

from flask import Flask, render_template

from plaid_client import get_transactions
from spending import compute_spending_summary

app = Flask(__name__)


@app.route("/")
def index():
    txns = get_transactions()
    summary = compute_spending_summary(txns, date.today())
    return render_template("index.html", summary=summary)


if __name__ == "__main__":
    app.run(debug=True)
