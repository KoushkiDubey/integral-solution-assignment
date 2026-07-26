"""
run_comparison.py -- run this to reproduce the before/after numbers.

Usage:
    python3 run_comparison.py
"""

from before import build_before_prompt
from after import build_after_prompt
from token_counter import count_tokens, is_approximate


def main():
    before = build_before_prompt()
    after = build_after_prompt()

    t_before = count_tokens(before)
    t_after = count_tokens(after)
    reduction = (1 - t_after / t_before) * 100
    label = "approximate (chars/4 heuristic -- no network access to pull a real " \
            "tokenizer in this sandbox; swap in tiktoken/Anthropic token-count " \
            "endpoint for production numbers)" if is_approximate() else "exact (cl100k_base)"

    print("=" * 70)
    print("TOKEN USAGE COMPARISON -- sample query:")
    print(f'  "{__import__("sample_data").SAMPLE_QUERY}"')
    print("=" * 70)
    print(f"BEFORE : {t_before:>7,} tokens  ({len(before):,} chars)")
    print(f"AFTER  : {t_after:>7,} tokens  ({len(after):,} chars)")
    print(f"REDUCTION: {reduction:.1f}%")
    print(f"(counts are {label})")


if __name__ == "__main__":
    main()
