"""
app/main.py -- small sample app so this repo has something real to
test, lint, and deploy. Stands in for "the provided repo" in Part 3.
"""

from flask import Flask, jsonify

app = Flask(__name__)


def calculate_refund_eta(days_since_request: int, method: str = "card") -> int:
    """Business logic kept separate from routes so it's easy to unit test."""
    if method not in ("card", "store_credit"):
        raise ValueError(f"unknown refund method: {method}")
    processing_days = 7 if method == "card" else 3
    remaining = processing_days - days_since_request
    return max(remaining, 0)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/refund-eta/<int:days_since_request>/<method>")
def refund_eta(days_since_request: int, method: str):
    try:
        eta = calculate_refund_eta(days_since_request, method)
        return jsonify({"days_remaining": eta})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
