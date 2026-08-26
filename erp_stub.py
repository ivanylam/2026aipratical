"""
AI & Analytics Engineer practical — Step 2 stub.

Do not modify post_to_erp(). Write your processing script around it,
either in this file or in your own file that imports from it.

The payloads to process are in po_payloads.json.
"""

import random


class ERPError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(f"{status}: {message}")


def post_to_erp(payload: dict) -> dict:
    """Stub for the ERP receiving endpoint. Do not modify."""
    roll = random.random()
    if roll < 0.25:
        raise ERPError(429, "rate limited, retry after 2s")
    if roll < 0.40:
        raise ERPError(500, "internal server error")
    if not payload.get("po_number"):
        raise ERPError(400, "po_number is required")
    return {"status": "ok", "erp_id": f"ERP-{payload['po_number']}"}
