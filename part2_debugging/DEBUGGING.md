# DEBUGGING.md — Debugging a flaky multi-step agent pipeline

## The reported symptoms
- Sometimes it times out
- Sometimes it returns malformed output
- Sometimes it silently succeeds with wrong data

Three different symptoms with three different root causes is normal for a
multi-step pipeline — each symptom usually points at a *different* step.
The process below is what I'd actually do, in order.

---

## Step 1 — Reproduce, and separate the symptoms

Before touching code, I'd stop treating this as "one flaky bug" and split
it into **three separate investigations**, because a fix for one won't
touch the others. First thing: try to reproduce each symptom on demand,
even if it's intermittent — run the pipeline in a loop (`demo_failures.py`
in this repo does exactly this) until each symptom shows up, and note the
**rate** (e.g. "malformed output ~1 in 5 calls", "timeout ~1 in 5 calls
under load"). A rough rate matters — it tells you whether you're chasing a
rare edge case or a common one, and rate changes are a good regression
signal later.

## Step 2 — Check logs/traces first, don't guess

For each symptom, pull:
- **Structured logs per step**, not just pipeline-level in/out. If the
  pipeline doesn't log at each step boundary yet, that's the first fix —
  add a `request_id` that's attached to every log line for that request,
  and log input/output (or at least shape/size) at each step. Without
  step-level logs, you're debugging blind.
- **Timing per step** — for the timeout symptom, I want to know *which*
  step is slow, not just that the whole pipeline was slow. If it's the
  external API call, that's an upstream latency problem, not a pipeline
  bug per se — but the pipeline should still fail fast instead of hanging.
- **The raw response body** right before the failure, for the malformed
  output symptom — I want to see the actual shape that broke parsing, not
  just the stack trace of where it broke.
- **Concurrency/timing context** for the silent-wrong-data symptom — this
  is the one where I'd specifically check: is this failure ever seen when
  requests run one at a time (sequentially), or only under concurrent
  load? That distinction alone tells me whether to look at shared state
  vs. a plain logic bug.

## Step 3 — Isolate: which step, which condition

**Timeout:**
Check whether there's an explicit timeout set on the external call at all.
A huge number of "intermittent timeout" bugs are simply *no timeout
configured* — the call just takes however long the upstream takes, and
under load or on a bad network day, that's minutes instead of milliseconds.
Confirm by adding a timeout locally and re-running: if the "timeout"
symptom turns into a clean, fast `TimeoutError` instead of an indefinite
hang, that confirms the root cause. (See `broken_pipeline.py` step 2 in
this repo — no timeout at all — vs. `fixed_pipeline.py` — explicit
per-attempt timeout + bounded retries.)

**Malformed output:**
Once I have a captured raw response that broke parsing, I diff it against
a known-good response. Usually it's one of: a missing field, a field that's
sometimes `null`, a differently-nested shape, or an error payload shaped
differently from a success payload but still returned with a 200-equivalent
status. I check whether the parsing step validates the shape *before* using
it, or just indexes straight into fields (`data["amount"]`) and hopes for
the best — that's the pattern to look for, because it turns "upstream sent
something odd" into "hard crash with no useful error", or worse, into a
silently-swallowed exception if there's a broad `try/except` somewhere
upstream in the call stack.

**Silent wrong data (the most dangerous one, because nothing alerts you):**
This is where I specifically look for **shared mutable state** — module-
level variables, class-level dicts used as ad-hoc caches, global counters,
anything not scoped to a single request — combined with concurrency
(multiple requests in flight, async tasks, thread pools). The tell-tale
sign: the bug disappears when you run requests one at a time, and appears
(with increasing frequency) as concurrency increases. I'd confirm this by
writing exactly the kind of test in `verify_fix.py` — fire N requests
concurrently, and assert that each response's identifying field
(`order_id` here) matches what was requested. If it doesn't, log the exact
line where shared state got written and read back — that's the race.

## Step 4 — Write a failing test that proves the root cause

Before fixing anything, I turn the reproduction into an actual test that
fails reliably (or fails at a known rate). For the concurrency bug
specifically, that means a test that fires many requests in parallel and
asserts response identity — a single-threaded test would never catch it,
which is itself a lesson: **tests for concurrency bugs must actually be
concurrent**, sequential tests will pass every time and give false
confidence.

## Step 5 — Fix, then re-run the same test to confirm

- Timeout → add an explicit timeout + bounded retry with backoff, fail
  loudly with a typed exception instead of hanging.
- Malformed output → validate required fields right after parsing, raise a
  specific typed error instead of an uncaught `KeyError` or a silently-
  swallowed generic exception.
- Silent wrong data → remove shared state; make sure every request's data
  flows through the pipeline as function arguments/return values only,
  never through a module-level or otherwise unscoped variable.

`fixed_pipeline.py` and `verify_fix.py` in this repo implement and prove
exactly this — running `verify_fix.py` repeatedly shows 0/20 mismatches
under concurrency, versus the broken version showing several per run.

## Step 6 — Add monitoring so this doesn't silently regress

The scariest symptom here is #3 — it doesn't throw, doesn't log an error,
it just quietly returns the wrong answer. A fix without monitoring can
regress silently again later (e.g. someone re-introduces a shared cache for
"performance"). I'd add:
- A cheap runtime assertion (`parsed["order_id"] == order_id` before
  returning) that raises loudly if it's ever violated in production —
  cheap insurance against exactly this class of bug coming back.
- Alerting on the *rate* of typed exceptions (timeout, malformed response)
  so a spike gets noticed instead of discovered by a customer.

---

## Summary — what I'd check first, in order
1. Reproduce and split the three symptoms into separate investigations.
2. Get/add step-level structured logs with a request ID before guessing.
3. For timeouts: check if there's an explicit timeout at all.
4. For malformed output: capture the actual bad payload, check for
   missing schema validation before fields are used.
5. For silent wrong data: look for shared mutable state + concurrency;
   confirm with a concurrent test, not a sequential one.
6. Fix each root cause with a typed, loud failure instead of a silent one.
7. Add a regression test + lightweight production assertion so it can't
   silently come back.
