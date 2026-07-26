"""
sample_data.py

Synthetic (hardcoded) data standing in for a real agent pipeline's context.
Scenario: a customer-support agent that answers order/refund questions.
It has run for several turns, has called a couple of tools, and now needs
to answer one more user question.

This is invented data, sized to realistically resemble what a ~100K-token
agent call looks like in production: a bloated raw API dump, full replayed
history, and an over-broad document retrieval -- the three usual suspects.
"""

import random

random.seed(42)

SAMPLE_QUERY = "What's the refund status for order #4521, and when will the money hit my card?"

SYSTEM_PROMPT = """You are a customer support agent for an e-commerce platform.
You have access to tools for looking up orders, refunds, and shipment status.
Always be polite, concise, and accurate. Never invent order details -- only use
information returned by tools. If a refund is pending, explain the typical
processing window (5-7 business days for cards, 2-3 for store credit)."""

TOOL_DEFINITIONS = [
    {
        "name": "get_order",
        "description": "Fetch full order record by order ID, including line items, "
                        "payment history, shipment tracking, refund history, customer "
                        "profile snapshot, warehouse routing metadata, and internal "
                        "fraud-check annotations.",
        "parameters": {"order_id": "string"},
    },
    {
        "name": "get_refund_status",
        "description": "Fetch refund status and ledger entries for a given order.",
        "parameters": {"order_id": "string"},
    },
    {
        "name": "search_kb",
        "description": "Full-text search over the support knowledge base.",
        "parameters": {"query": "string"},
    },
]

# --- Simulated RAW tool output (the "before" version pastes ALL of this) ---
# In real pipelines this is exactly what bloats context: a full DB record dump
# containing dozens of internal fields the agent doesn't need to answer a
# refund-status question.

def _fake_order_record(order_id: str) -> dict:
    return {
        "order_id": order_id,
        "customer": {
            "id": "cust_88213",
            "name": "Ananya Sharma",
            "email": "ananya.sharma@example.com",
            "phone": "+91-98xxxxxx21",
            "loyalty_tier": "gold",
            "loyalty_points": 4210,
            "account_created": "2021-03-14T10:22:00Z",
            "marketing_opt_in": True,
            "past_orders_count": 37,
            "lifetime_value_inr": 184320.50,
            "address_history": [
                {"line1": "Flat 12B, Sunrise Apartments", "city": "Varanasi", "pin": "221010"},
                {"line1": "Old Office Address", "city": "Lucknow", "pin": "226001"},
            ],
        },
        "line_items": [
            {"sku": "SKU-99231", "name": "Wireless Earbuds Pro", "qty": 1, "price_inr": 2999,
             "tax_inr": 179.94, "warehouse": "WH-DEL-03", "vendor_id": "V-4471",
             "return_window_days": 15, "category_tree": "Electronics/Audio/Earbuds"},
            {"sku": "SKU-11029", "name": "USB-C Cable 1m", "qty": 2, "price_inr": 199,
             "tax_inr": 11.94, "warehouse": "WH-DEL-03", "vendor_id": "V-2091",
             "return_window_days": 15, "category_tree": "Electronics/Accessories/Cables"},
        ],
        "payment": {
            "method": "credit_card", "card_last4": "4432", "gateway": "razorpay",
            "gateway_txn_id": "pay_NqX93kLzQ8mP", "auth_code": "A19273",
            "billing_address_verified": True, "amount_charged_inr": 3389.88,
        },
        "shipment": {
            "carrier": "Delhivery", "awb": "DLV772934821IN",
            "status": "delivered", "delivered_at": "2026-07-10T14:32:00Z",
            "route_history": [
                {"hub": "WH-DEL-03", "ts": "2026-07-06T09:00:00Z"},
                {"hub": "HUB-LKO-01", "ts": "2026-07-07T22:14:00Z"},
                {"hub": "HUB-VNS-02", "ts": "2026-07-09T06:40:00Z"},
                {"hub": "OFD-VNS", "ts": "2026-07-10T08:00:00Z"},
            ],
        },
        "refund": {
            "requested_at": "2026-07-18T11:05:00Z",
            "reason": "item_defective",
            "reason_notes": "Left earbud not charging, customer provided video proof.",
            "status": "processing",
            "refund_id": "rfnd_88213X",
            "amount_inr": 3389.88,
            "ledger_entries": [
                {"ts": "2026-07-18T11:05:00Z", "event": "refund_requested"},
                {"ts": "2026-07-18T11:07:00Z", "event": "auto_approved_low_risk"},
                {"ts": "2026-07-19T09:00:00Z", "event": "warehouse_return_received"},
                {"ts": "2026-07-19T09:15:00Z", "event": "refund_initiated_to_gateway"},
            ],
            "expected_completion": "2026-07-24T00:00:00Z",
            "fraud_check": {"score": 0.02, "flags": [], "reviewer": "auto"},
        },
        "internal_notes": "Customer is gold tier -- prioritize. Vendor V-4471 has "
                          "elevated defect rate this quarter, flagged for QA review "
                          "(unrelated to this ticket, do not mention to customer).",
    }

RAW_TOOL_OUTPUT = _fake_order_record("4521")

# --- Simulated conversation history (the "before" version replays ALL turns) ---

def _fake_history(n_turns: int = 10) -> list:
    turns = []
    topics = [
        "asking about shipping delay on a different order",
        "asking how to change delivery address",
        "asking about a discount coupon that didn't apply",
        "asking about warranty on a laptop stand",
        "asking about return pickup scheduling",
        "asking about invoice GST details",
        "small talk / greeting",
        "asking about loyalty points expiry",
        "asking about payment method update",
        "asking about order #4521 refund (leads into current query)",
    ]
    for i in range(n_turns):
        turns.append({"role": "user", "content": f"[Turn {i+1}] Customer message about: {topics[i % len(topics)]}. "
                      + ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 190)})
        turns.append({"role": "assistant", "content": f"[Turn {i+1}] Agent response addressing: {topics[i % len(topics)]}. "
                      + ("Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. " * 190)})
    return turns

CONVERSATION_HISTORY = _fake_history(10)

# --- Simulated over-broad KB retrieval (the "before" version dumps whole articles) ---

RETRIEVED_KB_ARTICLES = [
    {
        "title": "Refund Policy - Full Terms and Conditions",
        "content": ("This document covers our complete refund policy including edge cases "
                    "for international orders, marketplace vendor items, digital goods, "
                    "subscription cancellations, partial refunds, store credit conversions, "
                    "chargeback handling, and dispute resolution timelines. " * 315),
    },
    {
        "title": "Payment Gateway Processing Times - All Methods",
        "content": ("Detailed breakdown of processing times for every supported payment "
                    "method including credit cards, debit cards, UPI, net banking, wallets, "
                    "EMI, and cash on delivery reversal procedures across all partner banks. " * 315),
    },
]

if __name__ == "__main__":
    print("Sample query:", SAMPLE_QUERY)
    print("Raw tool output keys:", list(RAW_TOOL_OUTPUT.keys()))
    print("History turns:", len(CONVERSATION_HISTORY))
    print("KB articles:", len(RETRIEVED_KB_ARTICLES))
