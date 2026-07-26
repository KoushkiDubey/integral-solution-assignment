"""
demo_failures.py

Runs the broken pipeline repeatedly (including concurrently, to trigger the
race condition) and prints what actually happens -- reproducing all three
symptoms described in the assignment:
  - intermittent timeout / slow hang
  - intermittent malformed output (crash)
  - intermittent silent wrong data (no crash, no error, wrong answer)

Run: python3 demo_failures.py
"""

import time
import threading
from broken_pipeline import run_pipeline


def run_sequential_demo(n=15):
    print("=== Sequential runs (surfaces BUG 1 timeout + BUG 2 malformed output) ===")
    for i in range(n):
        order_id = f"ORDER-{1000+i}"
        start = time.time()
        try:
            result = run_pipeline(order_id)
            elapsed = time.time() - start
            flag = "  <-- SLOW (looks like a timeout under real latency budgets)" if elapsed > 1.0 else ""
            print(f"[{i}] {order_id}: OK in {elapsed:.2f}s -> {result}{flag}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"[{i}] {order_id}: FAILED in {elapsed:.2f}s -> {type(e).__name__}: {e}")


def run_concurrent_demo(n=8):
    print("\n=== Concurrent runs (surfaces BUG 3: silent wrong data via shared cache) ===")
    results = {}
    order_ids = [f"ORDER-{2000+i}" for i in range(n)]

    def worker(oid):
        try:
            results[oid] = run_pipeline(oid)
        except Exception as e:
            results[oid] = f"ERROR: {e}"

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
            print(f"  MISMATCH: requested {oid}, got data for {r.get('order_id')}  -> {r}")
        else:
            print(f"  OK: {oid} -> {r}")
    print(f"\n{mismatches}/{n} requests returned another request's data silently (no exception raised).")


if __name__ == "__main__":
    run_sequential_demo()
    run_concurrent_demo()
