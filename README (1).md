# AI Systems Assignment — Cost Optimization, Debugging, CI/CD

Submission for the take-home assessment covering three areas: token/cost
optimization in an agent pipeline, debugging an intermittently-failing
multi-step workflow, and setting up a CI/CD pipeline with a rollback plan.

Each part has its own folder with runnable code and its own README with
full detail. This file is a summary/index.

---

## Part 1 — Token / Cost Optimization
📁 [`part1_token_optimization/`](./part1_token_optimization)

**Problem:** an agent pipeline burning ~100K input tokens per query.

**What I did:** identified the three usual sources of context bloat (raw
tool output dumps, full conversation history replay, whole-document
retrieval) and implemented three fixes: trimming tool output to only
relevant fields, summarizing old conversation turns while keeping recent
ones verbatim, and retrieving targeted snippets instead of whole documents.

**Result (reproducible — run `python3 run_comparison.py`):**

| | Tokens |
|---|---|
| Before | 97,571 |
| After | 653 |
| Reduction | 99.3% |

Full writeup, quality tradeoffs, and note on prompt caching as a separate
cost lever: see [`part1_token_optimization/README.md`](./part1_token_optimization/README.md).

---

## Part 2 — Debugging a Flaky Pipeline
📁 [`part2_debugging/`](./part2_debugging)

**Problem:** a multi-step agent workflow that intermittently times out,
returns malformed output, or silently succeeds with wrong data.

**What I did:** built a small runnable pipeline reproducing all three
failure modes on purpose (`broken_pipeline.py`), documented the actual
debugging process step by step — what to check first, what logs/tools to
pull, how to isolate each root cause (`DEBUGGING.md`) — then fixed all
three (`fixed_pipeline.py`) and proved the fix holds under concurrency
(`verify_fix.py`, 0/20 mismatches across repeated runs vs. several per run
on the broken version).

The three root causes: no timeout on an external call, no schema
validation before indexing into a parsed response, and a shared
module-level cache causing cross-request data leaks under concurrency.

Full process: see [`part2_debugging/DEBUGGING.md`](./part2_debugging/DEBUGGING.md).

---

## Part 3 — CI/CD and Deployment
📁 [`part3_cicd/`](./part3_cicd)

**What I did:** a small Flask sample app with unit tests, wired to a
GitHub Actions pipeline (`.github/workflows/ci-cd.yml`) that:
- runs lint (`ruff`) + tests (`pytest`) on every push and PR
- deploys to staging automatically on merge to `main`, only if tests
  passed, followed by a health-check smoke test

Also covered: how secrets/API keys are handled (GitHub Actions Secrets,
scoped to a `staging` environment, least-privilege, rotatable, never in
code), and the rollback plan for a broken production deploy — first move
is always rolling back to the last known-good version, not debugging
forward under pressure.

Full detail: see [`part3_cicd/README.md`](./part3_cicd/README.md).

---

## How to verify everything locally

```bash
# Part 1
cd part1_token_optimization
python run_comparison.py

# Part 2
cd ../part2_debugging
python demo_failures.py   # see the bugs
python verify_fix.py      # see them fixed

# Part 3
cd ../part3_cicd
pip install -r requirements.txt
pytest -v
ruff check .
```
