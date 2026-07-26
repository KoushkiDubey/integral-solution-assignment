# Part 2 — Debugging a Flaky Multi-Step Agent Pipeline

## Files
- **`broken_pipeline.py`** — a small 4-step pipeline (build request → call
  external API → parse response → aggregate) with all three bugs from the
  brief deliberately built in.
- **`demo_failures.py`** — run this to trigger and see all three symptoms:
  timeout, malformed output crash, and silent wrong data under concurrency.
- **`DEBUGGING.md`** — the actual step-by-step investigation process: what
  I'd check first, what logs/tools I'd pull, how I'd isolate each root
  cause. **This is the main deliverable for Part 2** — read this one for
  the interview.
- **`fixed_pipeline.py`** — same pipeline, each bug fixed, with comments
  explaining exactly what changed and why.
- **`verify_fix.py`** — proves the fixes hold under concurrency (run it a
  few times — always 0 mismatches, vs. `demo_failures.py` showing several
  per run on the broken version).

## Quick way to see it in action
```bash
cd part2_debugging
python3 demo_failures.py     # see the bugs happen
python3 verify_fix.py        # see them fixed
```

## The three bugs, one line each
1. **Timeout** — the "API call" step had no timeout set at all, so an
   occasional slow response just hangs the whole pipeline instead of
   failing fast.
2. **Malformed output** — the parse step indexed straight into fields
   (`data["amount"]`) with no schema validation, so an upstream response
   missing a field caused an uncaught `KeyError` instead of a clear error.
3. **Silent wrong data** — the aggregate step read from a shared,
   module-level cache instead of using the current request's own data, so
   under concurrent requests one request's result could leak into
   another's response — with no exception raised at all.

Full reasoning for how each was found and fixed is in `DEBUGGING.md`.
