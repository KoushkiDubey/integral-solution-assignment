"""
fixed_pipeline.py

Same pipeline, with the three root causes fixed. Each fix directly maps to
a bug found via the process in DEBUGGING.md.

FIX 1 (timeout)         -> explicit timeout + retry/backoff wrapping the
                            external call, so a slow call fails fast and
                            loud instead of hanging indefinitely.
FIX 2 (malformed output) -> schema validation immediately after parsing,
                            with a clear, specific exception instead of an
                            uncaught/broadly-caught KeyError.
FIX 3 (silent wrong data) -> removed the shared module-level cache; each
                            request carries its own data through the
                            pipeline with no shared mutable state.
"""

import random
import time
import json


class UpstreamTimeoutError(Exception):
    pass


class MalformedResponseError(Exception):
    pass


def step1_build_request(order_id: str) -> dict:
    return {"order_id": order_id, "fields": ["status", "amount"]}


def step2_call_external_api(request: dict, timeout_seconds: float = 1.0, max_retries: int = 2) -> str:
    """FIX 1: explicit timeout per attempt + bounded retries with backoff.
    A call that would have hung for 4.5s now fails fast at the timeout
    boundary instead of blocking the whole pipeline."""
    last_error = None
    for attempt in range(max_retries + 1):
        start = time.time()
        simulated_latency = random.choice([0.01, 0.02, 0.01, 4.5, 0.02])

        if simulated_latency > timeout_seconds:
            last_error = UpstreamTimeoutError(
                f"attempt {attempt}: upstream exceeded {timeout_seconds}s timeout"
            )
            continue  # retry instead of hanging

        time.sleep(simulated_latency)

        if random.random() < 0.2:
            return json.dumps({"order_id": request["order_id"], "status": "processing"})
        return json.dumps({
            "order_id": request["order_id"],
            "status": "processing",
            "amount": round(random.uniform(500, 5000), 2),
        })

    raise last_error


def step3_parse_response(raw_response: str) -> dict:
    """FIX 2: validate the shape before using it. Fails loudly and
    specifically (MalformedResponseError) instead of an uncaught KeyError
    somewhere downstream, or worse, a broad except swallowing it silently."""
    data = json.loads(raw_response)
    required_fields = ("order_id", "status", "amount")
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise MalformedResponseError(
            f"upstream response missing required field(s) {missing}: {data}"
        )
    return {
        "order_id": data["order_id"],
        "status": data["status"],
        "amount": data["amount"],
    }


def step4_aggregate(order_id: str, parsed: dict) -> dict:
    """FIX 3: no shared/module-level state at all. The result is built
    purely from this request's own `parsed` data, so concurrent requests
    cannot leak into each other regardless of thread interleaving."""
    assert parsed["order_id"] == order_id, "sanity check: pipeline built result for wrong order"
    return dict(parsed)  # return a fresh copy, not a reference to shared state


def run_pipeline(order_id: str) -> dict:
    req = step1_build_request(order_id)
    raw = step2_call_external_api(req)
    parsed = step3_parse_response(raw)
    result = step4_aggregate(order_id, parsed)
    return result


if __name__ == "__main__":
    print(run_pipeline("ORDER-1001"))
