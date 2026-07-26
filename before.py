"""
before.py -- THE UNOPTIMIZED PIPELINE

This is what the agent sends to the model today, for the sample query.
Problems (see README.md for full explanation):
  1. Full raw tool output (entire DB record) pasted into context, including
     dozens of fields irrelevant to a refund-status question.
  2. Full conversation history replayed verbatim on every call, including
     turns about completely unrelated topics.
  3. Entire KB articles dumped in rather than the relevant paragraph.
"""

import json
from sample_data import (
    SYSTEM_PROMPT, TOOL_DEFINITIONS, RAW_TOOL_OUTPUT,
    CONVERSATION_HISTORY, RETRIEVED_KB_ARTICLES, SAMPLE_QUERY,
)
from token_counter import count_tokens, is_approximate


def build_before_prompt() -> str:
    parts = [SYSTEM_PROMPT]
    parts.append("TOOLS:\n" + json.dumps(TOOL_DEFINITIONS, indent=2))

    parts.append("CONVERSATION HISTORY:")
    for turn in CONVERSATION_HISTORY:
        parts.append(f"{turn['role'].upper()}: {turn['content']}")

    parts.append("TOOL RESULT (get_order, raw):")
    parts.append(json.dumps(RAW_TOOL_OUTPUT, indent=2))

    parts.append("RETRIEVED KNOWLEDGE BASE ARTICLES (full text):")
    for art in RETRIEVED_KB_ARTICLES:
        parts.append(f"## {art['title']}\n{art['content']}")

    parts.append(f"USER: {SAMPLE_QUERY}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    prompt = build_before_prompt()
    tokens = count_tokens(prompt)
    label = "~approx" if is_approximate() else "exact (cl100k_base)"
    print(f"[BEFORE] chars={len(prompt):,}  tokens={tokens:,} ({label})")
