from flask import Flask, render_template
from plaid_client import get_balances

app = Flask(__name__)


@app.route("/")
def index():
    accounts = get_balances()
    return render_template("index.html", accounts=accounts)


if __name__ == "__main__":
    app.run(debug=True)
