"""
Author: Ivan Lam
Context: Purchase order confirmations arrive as webhook payloads and have to be written into the ERP. The ERP's API is not well behaved. Write a script (Python or JavaScript) that processes the payloads below through the provided stub. It should survive being run against a flaky endpoint and be safe to re-run.

Results:
Handled: retry 429 (wait 2s as the API says) and 500 (backoff); do not retry 400s;
skip blank po_number; write successes to posted_pos.json so a re-run does not double-post.
Left out: guessing a missing PO number; rejecting empty line lists (the stub accepts them);
treating a later payload with the same PO as an amendment — that needs a human rule.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from erp_stub import ERPError, post_to_erp

PAYLOADS_PATH = Path(__file__).with_name("po_payloads.json")
LEDGER_PATH = Path(__file__).with_name("posted_pos.json")

MAX_ATTEMPTS = 8
BACKOFF_START_SECONDS = 1.0


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    tmp.replace(path)


def retry_wait_seconds(err: ERPError, attempt: int) -> float | None:
    """Return how long to wait, or None if this error should not be retried."""
    if err.status == 429:
        return 2.0
    if err.status >= 500:
        return BACKOFF_START_SECONDS * (2 ** (attempt - 1))
    return None


def post_with_retry(payload: dict) -> dict:
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return post_to_erp(payload)
        except ERPError as err:
            last_error = err
            wait = retry_wait_seconds(err, attempt)
            if wait is None:
                raise
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"    {err} - retry {attempt}/{MAX_ATTEMPTS} in {wait:.0f}s")
            time.sleep(wait)
    raise last_error


def process(payloads: list[dict]) -> list[dict]:
    ledger = load_json(LEDGER_PATH, {})
    results = []

    for i, payload in enumerate(payloads, start=1):
        po = (payload.get("po_number") or "").strip()
        supplier = payload.get("supplier", "")
        label = po or f"(blank po, row {i})"
        print(f"[{i}/{len(payloads)}] {label} / {supplier}")

        if not po:
            print("    skip: po_number is required; not posting")
            results.append({"po_number": "", "outcome": "rejected", "reason": "missing po_number"})
            continue

        if po in ledger:
            print(f"    skip: already posted as {ledger[po]['erp_id']}")
            results.append({"po_number": po, "outcome": "skipped_duplicate", "erp_id": ledger[po]["erp_id"]})
            continue

        if not payload.get("lines"):
            print("    warning: no line items - posting anyway; ERP stub does not reject this")

        try:
            response = post_with_retry(payload)
        except ERPError as err:
            print(f"    failed: {err}")
            results.append({"po_number": po, "outcome": "failed", "reason": str(err)})
            continue

        ledger[po] = {"erp_id": response["erp_id"], "status": response["status"]}
        save_json(LEDGER_PATH, ledger)
        print(f"    posted as {response['erp_id']}")
        results.append({"po_number": po, "outcome": "posted", "erp_id": response["erp_id"]})

    return results


def main() -> int:
    payloads = load_json(PAYLOADS_PATH, None)
    if not isinstance(payloads, list):
        print(f"Could not read a JSON list from {PAYLOADS_PATH}", file=sys.stderr)
        return 1

    results = process(payloads)
    posted = sum(1 for r in results if r["outcome"] == "posted")
    skipped = sum(1 for r in results if r["outcome"] == "skipped_duplicate")
    rejected = sum(1 for r in results if r["outcome"] == "rejected")
    failed = sum(1 for r in results if r["outcome"] == "failed")
    print(
        f"\nDone. posted={posted} skipped_duplicate={skipped} "
        f"rejected={rejected} failed={failed}"
    )
    print(f"Ledger: {LEDGER_PATH}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
