# Part 1 — Token / Cost Optimization

## Scenario
An agent pipeline (customer-support agent, order/refund lookups) burns ~100K
input tokens per query. `sample_data.py` hardcodes one representative query
and a realistic bloated context around it, sized to land near 100K tokens,
so the before/after comparison is reproducible.

**Sample query:** `"What's the refund status for order #4521, and when will
the money hit my card?"`

## Where the tokens were going (before)
Broken down, the ~97.5K "before" tokens came from:

| Source | What was wrong |
|---|---|
| Raw tool output (`get_order`) | Entire DB record pasted in — customer PII, address history, warehouse routing, fraud scores, internal QA notes — none of which the agent needs to answer a refund-status question |
| Conversation history | All 10 prior turns replayed verbatim every call, including turns about unrelated topics (coupon issues, loyalty points, address changes) |
| KB retrieval | Two full policy documents pasted in whole, instead of the one or two sentences actually relevant |

## Optimizations implemented

**1. Trim tool output to only relevant fields** (`after.py::trim_order_record`)
Instead of forwarding the full `get_order` response, extract just the fields
needed to answer refund questions (status, amount, dates, payment method).
This assumes the tool call itself could also be made narrower — e.g. calling
`get_refund_status` instead of the full `get_order` — but even if the tool
must return the full record, trimming before it re-enters context works.

**2. Summarize old conversation turns, keep only recent ones verbatim**
(`after.py::summarize_old_turns`)
Turns unrelated to the current topic get collapsed into one short rolling
summary line; only the most recent turn(s) are kept in detail. In production
this summary would be generated once by a cheap background call and cached/
updated incrementally, not regenerated from scratch every request.

**3. Retrieve targeted snippets instead of whole documents**
(`after.py::targeted_kb_snippets`)
Stands in for proper paragraph/sentence-level chunking in the retrieval
step, so only the 1-2 sentences relevant to "when does a refund post" come
back, not entire policy documents.

**Not implemented in code here, but worth mentioning in the interview:**
**Prompt caching** — the system prompt and tool definitions are identical on
every call. Using the API's prompt caching means those tokens are only
processed/billed once instead of on every single request. This is a distinct
lever from the three above: it doesn't reduce the token *count* you'd measure
per call, but it cuts real-world cost and latency significantly for anything
called repeatedly with a stable prefix.

## Results

Run it yourself:
```bash
cd part1_token_optimization
python3 run_comparison.py
```

| | Tokens | Chars |
|---|---|---|
| **Before** | 97,571 | 390,287 |
| **After** | 653 | 2,615 |
| **Reduction** | **99.3%** | |

> Note on counting: this sandbox has no network access, so `token_counter.py`
> falls back to a documented `len(text) // 4` approximation (the standard
> ballpark heuristic for English text across GPT/Claude-family tokenizers,
> ±10-15% in practice) when `tiktoken` can't download its encoding file. The
> code auto-switches to exact `tiktoken` counts if it's available. For a
> real production number, swap in Anthropic's token-count endpoint.

The reduction looks extreme (99%) because the hardcoded "before" scenario
deliberately reproduces the worst version of each bloat source (full DB
dump, full history replay, full document dump) to make each optimization's
effect clearly visible. In a real system the starting point is usually less
extreme, but the same three sources — raw tool dumps, full history replay,
whole-document retrieval — are the ones to check first, in that order,
because they're consistently the biggest offenders.

## Quality tradeoffs

| Optimization | Tradeoff / risk |
|---|---|
| Trimming tool output | If a later step in the agent's chain needs a field that got dropped (e.g. warehouse info for a shipping question), it has to re-fetch it — need to be deliberate about which fields are "safe to drop" per task type, not a blanket filter |
| Summarizing history | Risk of losing a detail buried in an "unrelated" earlier turn that turns out to matter later (e.g. customer already mentioned a related complaint) — mitigated by keeping the last 1-2 turns verbatim and re-summarizing incrementally rather than throwing away raw turns entirely (keep them in a DB, just don't replay them in-context) |
| Targeted retrieval vs full docs | Depends entirely on retrieval/chunking quality — if the retriever misses the right paragraph, the agent gives a worse answer than if it had the whole document. This is the tradeoff most worth testing/monitoring in production (retrieval recall vs context size) |
| Prompt caching (not shown in token count) | No quality tradeoff — it's a cost/latency win with no behavior change, since the model still sees the same content. Only catch is cache invalidates if the static prefix changes, so it's most valuable when system prompt/tools are genuinely stable |
