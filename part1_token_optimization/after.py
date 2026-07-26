"""
after.py -- THE OPTIMIZED PIPELINE

Applies three concrete changes to the same sample query:

  OPTIMIZATION 1 -- Trim tool output to only the fields the task needs.
    Instead of dumping the full order record (customer PII, address history,
    warehouse routing, fraud scores, internal notes...), extract only the
    refund-relevant fields before they go back into context.

  OPTIMIZATION 2 -- Summarize old conversation turns, keep recent ones verbatim.
    Instead of replaying all 10 raw turns, collapse turns unrelated to the
    current topic into a one-line rolling summary, and keep only the most
    recent turn (which is actually about this order) in full.

  OPTIMIZATION 3 -- Retrieve targeted snippets, not whole KB articles.
    Instead of pasting entire policy documents, pull just the relevant
    sentence(s) (this is what a real embedding-based retriever would return
    if chunked properly at the paragraph/sentence level instead of whole-doc).

  (A fourth lever, prompt caching, is discussed in README.md -- it doesn't
  show up as a token-count reduction here because it's a cost/latency
  optimization, not a token-count optimization: the static system prompt +
  tool defs get cached by the API instead of reprocessed every call.)
"""

import json
from sample_data import (
    SYSTEM_PROMPT, TOOL_DEFINITIONS, RAW_TOOL_OUTPUT,
    CONVERSATION_HISTORY, SAMPLE_QUERY,
)
from token_counter import count_tokens, is_approximate


def trim_order_record(raw: dict) -> dict:
    """OPTIMIZATION 1: keep only fields relevant to a refund-status question."""
    refund = raw["refund"]
    return {
        "order_id": raw["order_id"],
        "refund_status": refund["status"],
        "refund_amount_inr": refund["amount_inr"],
        "refund_requested_at": refund["requested_at"],
        "refund_expected_completion": refund["expected_completion"],
        "payment_method": raw["payment"]["method"],
        "card_last4": raw["payment"].get("card_last4"),
    }


def summarize_old_turns(history: list, keep_last_n: int = 2) -> str:
    """OPTIMIZATION 2: collapse older/unrelated turns into a short summary,
    keep only the most recent turns verbatim."""
    older = history[:-keep_last_n] if keep_last_n else history
    recent = history[-keep_last_n:] if keep_last_n else []

    # In a real system this summary would be produced once (e.g. by a cheap
    # background summarization call) and cached/reused, not regenerated from
    # scratch every turn. Here we hardcode the equivalent summary output.
    summary = (
        "Earlier in this conversation the customer asked about: a shipping delay "
        "on a different order, changing a delivery address, a coupon that didn't "
        "apply, warranty on a laptop stand, return pickup scheduling, GST invoice "
        "details, a greeting, loyalty points expiry, and updating a payment method. "
        "All were resolved; none are relevant to the current question about order #4521."
    )
    lines = [f"[SUMMARY OF {len(older)} EARLIER TURNS]: {summary}"]
    for turn in recent:
        lines.append(f"{turn['role'].upper()}: {turn['content'][:200]}...")  # recent turns kept, but trimmed of filler
    return "\n".join(lines)


def targeted_kb_snippets() -> str:
    """OPTIMIZATION 3: only the retrieved snippet relevant to the query,
    not the full source articles."""
    return (
        "- Refund Policy: card refunds are typically processed within 5-7 business "
        "days after the returned item is received by the warehouse.\n"
        "- Payment Gateway Processing Times: credit card reversals via Razorpay "
        "typically post to the customer's statement within 3-5 business days after "
        "the refund is initiated on our end."
    )


def build_after_prompt() -> str:
    parts = [SYSTEM_PROMPT]
    parts.append("TOOLS:\n" + json.dumps(TOOL_DEFINITIONS, indent=2))

    parts.append("CONVERSATION CONTEXT:\n" + summarize_old_turns(CONVERSATION_HISTORY))

    trimmed = trim_order_record(RAW_TOOL_OUTPUT)
    parts.append("TOOL RESULT (get_refund_status, trimmed to relevant fields):")
    parts.append(json.dumps(trimmed, indent=2))

    parts.append("RELEVANT POLICY SNIPPETS:")
    parts.append(targeted_kb_snippets())

    parts.append(f"USER: {SAMPLE_QUERY}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    prompt = build_after_prompt()
    tokens = count_tokens(prompt)
    label = "~approx" if is_approximate() else "exact (cl100k_base)"
    print(f"[AFTER] chars={len(prompt):,}  tokens={tokens:,} ({label})")
