"""
broken_pipeline.py

A small, self-contained simulation of a "multi-step agent workflow" that
intermittently fails in exactly the three ways described in the assignment:

  1. Sometimes it TIMES OUT      -> step 2 (external API call) has unbounded,
                                     randomly-slow latency and no timeout set.
  2. Sometimes it returns
     MALFORMED OUTPUT            -> step 3 (parse) assumes a JSON shape that
                                     the upstream API doesn't always honor,
                                     and there's no schema validation before
                                     the field is used.
  3. Sometimes it SILENTLY
     SUCCEEDS WITH WRONG DATA    -> step 4 (aggregate) reads from a shared
                                     module-level cache without any request
                                     isolation, so under concurrent requests
                                     one request's result can leak into
                                     another's response. No error is raised;
                                     the pipeline returns 200 with wrong data.

This file is deliberately runnable and deliberately buggy -- run
`python3 demo_failures.py` to see each failure mode triggered on repeated
runs, exactly as it would look in a flaky production system.

See DEBUGGING.md for the actual investigation process, and
fixed_pipeline.py for the corrected version with the reasoning for each fix.
"""

import random
import time
import json

# BUG 3 setup: module-level "cache" shared across all requests/threads.
# This is the classic root cause of "silently returns wrong data" --
# nothing here is scoped to a single request.
_last_result_cache = {}


def step1_build_request(order_id: str) -> dict:
    return {"order_id": order_id, "fields": ["status", "amount"]}


def step2_call_external_api(request: dict) -> str:
    """BUG 1: no timeout on the 'network call'. Latency is randomly
    slow (simulating a flaky upstream), and nothing bounds how long
    the agent will wait."""
    simulated_latency = random.choice([0.01, 0.02, 0.01, 4.5, 0.02])  # occasional huge spike
    time.sleep(simulated_latency)  # <-- no timeout wrapping this call anywhere

    # Simulate the upstream occasionally returning a slightly different
    # shape (e.g. a schema change that wasn't communicated, or an error
    # payload that isn't shaped like a success payload).
    if random.random() < 0.2:
        # malformed / unexpected shape -- missing "amount", or wrapped differently
        return json.dumps({"order_id": request["order_id"], "status": "processing"})
    return json.dumps({
        "order_id": request["order_id"],
        "status": "processing",
        "amount": round(random.uniform(500, 5000), 2),
    })


def step3_parse_response(raw_response: str) -> dict:
    """BUG 2: parses and immediately indexes into fields with no schema
    validation. If step2 returned the malformed shape, this throws a
    KeyError -- or worse, in some code paths, gets caught by an overly
    broad try/except higher up and silently swallowed."""
    data = json.loads(raw_response)
    return {
        "order_id": data["order_id"],
        "status": data["status"],
        "amount": data["amount"],  # <-- KeyError if "amount" missing, uncaught here
    }


def step4_aggregate(order_id: str, parsed: dict) -> dict:
    """BUG 3: writes to and reads from a shared, unscoped cache. Under
    concurrent requests (e.g. two orders processed close together), a
    race condition means this can return the PREVIOUS request's data
    instead of the current one -- with no exception raised at all."""
    global _last_result_cache
    _last_result_cache["last"] = parsed  # overwritten by any concurrent call
    time.sleep(random.choice([0.0, 0.05]))  # simulate other work happening in between
    # BUG: reads back from the shared cache instead of using `parsed` directly
    return _last_result_cache["last"]


def run_pipeline(order_id: str) -> dict:
    req = step1_build_request(order_id)
    raw = step2_call_external_api(req)
    parsed = step3_parse_response(raw)
    result = step4_aggregate(order_id, parsed)
    return result


if __name__ == "__main__":
    print(run_pipeline("ORDER-1001"))
