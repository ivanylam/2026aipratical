# PO confirmation ingest

Runnable Step 2 for the AI & Analytics Engineer practical.

## Run

```bash
python process_po_confirmations.py
```

Python 3.10+. No third-party packages.

The first run posts new POs through the flaky ERP stub. Run it again: already-posted POs are skipped (see `posted_pos.json`).

## Files

- `process_po_confirmations.py` — ingest, retries, idempotency
- `erp_stub.py` — provided stub; `post_to_erp()` is not modified
- `po_payloads.json` — sample webhook payloads
