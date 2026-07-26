"""
token_counter.py

Counts tokens for a given text.

- If `tiktoken` is installed and reachable, uses cl100k_base (GPT-family) encoding
  as a stand-in tokenizer, since it's the most widely available offline-installable
  tokenizer and gives a realistic ballpark for any modern LLM.
- If tiktoken is not available (e.g. no network access to pull the encoding file,
  as in this sandboxed environment), falls back to a documented approximation:

      tokens ~= len(text) / 4

  This 4-chars-per-token heuristic is a well-known, widely-cited approximation for
  English text across GPT/Claude-family tokenizers (+/- 10-15% in practice). It is
  clearly labeled as an approximation everywhere it's used in this repo. In a real
  submission, swap this for the actual model's tokenizer (e.g. Anthropic's token
  counting endpoint, or tiktoken) before reporting final numbers to a stakeholder.
"""

def count_tokens(text: str) -> int:
    try:
        import tiktoken  # noqa
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback approximation -- documented above.
        return max(1, len(text) // 4)


def is_approximate() -> bool:
    """Lets calling scripts label output as exact vs approximate."""
    try:
        import tiktoken  # noqa
        tiktoken.get_encoding("cl100k_base")
        return False
    except Exception:
        return True


if __name__ == "__main__":
    sample = "This is a quick sanity check of the token counter."
    print(f"approx={is_approximate()}  tokens={count_tokens(sample)}")
