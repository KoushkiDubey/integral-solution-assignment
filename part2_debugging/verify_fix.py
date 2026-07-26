"""
verify_fix.py -- proves the fixes actually work.

Run: python3 verify_fix.py
"""

import threading
from fixed_pipeline import run_pipeline, UpstreamTimeoutError, MalformedResponseError


def verify_concurrent(n=20):
    results = {}
    order_ids = [f"ORDER-{3000+i}" for i in range(n)]

    def worker(oid):
        try:
            results[oid] = run_pipeline(oid)
        except (UpstreamTimeoutError, MalformedResponseError) as e:
            # These are now EXPECTED, explicit, typed failures -- not silent
            # wrong data. Retries/alerting can hook in here cleanly.
            results[oid] = f"HANDLED ERROR ({type(e).__name__}): {e}"

    threads = [threading.Thread(target=worker, args=(oid,)) for oid in order_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    mismatches = 0
    for oid in order_ids:
        r = results[oid]
        if isinstance(r, dict) and r.get("order_id") != oid:
            mismatches += 1
            print(f"  MISMATCH: {oid} -> {r}")
        else:
            print(f"  OK: {oid} -> {r}")

    print(f"\n{mismatches}/{n} silent data mismatches (should always be 0 now).")
    assert mismatches == 0, "FIX 3 regression: cross-request data leak still happening"
    print("PASS: no cross-request data leaks under concurrency.")


if __name__ == "__main__":
    print("=== Verifying fixed pipeline under concurrency (20 parallel requests) ===")
    verify_concurrent()
