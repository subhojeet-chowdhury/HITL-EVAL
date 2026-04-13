"""
backend/api/label.py
────────────────────
The labeling endpoints — the "consumer" side of the queue.

  GET  /label/next    → pop the next item from Redis for the labeler to see
  POST /label/{id}    → submit a verdict (good/bad/edited)
  POST /label/{id}/skip → skip this item (push it back or discard)

LESSON — Long-polling pattern:
The UI calls GET /label/next repeatedly. If the queue is empty, the
endpoint *blocks* for up to 5 seconds (BRPOP timeout), then returns 204.
The UI shows "Queue empty, waiting..." and polls again.

This is called **long-polling** — it's simpler than WebSockets and works
well for low-volume labeling workloads. For high-volume, consider SSE
(Server-Sent Events) or WebSockets.

LESSON — Idempotency:
POST /label/{id} checks if the item is already labeled before writing.
This prevents duplicate labels if the UI submits twice (e.g., double-click).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.queue import eval_queue
from backend.db.models import EvalItem, Label
from backend.db.session import get_db_session
from backend.observability.tracing import record_label

router = APIRouter(prefix="/label", tags=["label"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class NextItemResponse(BaseModel):
    item_id: str
    prompt: str
    output: str
    prompt_id: str
    model: str | None
    enqueued_at: str
    queue_depth: int


class LabelRequest(BaseModel):
    verdict: str = Field(..., pattern="^(good|bad|edited)$")
    corrected_output: str | None = Field(None, description="Required if verdict is 'edited'")
    note: str | None = Field(None, description="Optional free-text note")
    labeler_id: str | None = Field(None, description="Who is labeling? (username, email, etc.)")


class LabelResponse(BaseModel):
    item_id: str
    verdict: str
    message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/next", response_model=NextItemResponse | None)
async def get_next_item():
    """
    Pop the next item from the queue for labeling.

    Returns 204 No Content if the queue is empty after waiting.
    Returns the item as JSON if one is available.

    LESSON — Why pop from queue here and not on the frontend?
    The queue is server-side (Redis). The frontend can't talk to Redis directly.
    The frontend talks to our FastAPI server, which talks to Redis.
    This also lets us add auth, rate limiting, etc. in one place.
    """
    item = await eval_queue.dequeue(timeout=5)

    if item is None:
        # 204 = "I understood your request and it's valid, but there's nothing to return"
        # Don't use 404 here — the queue being empty isn't an error
        return None

    depth = await eval_queue.depth()
    return NextItemResponse(
        item_id=item["item_id"],
        prompt=item["prompt"],
        output=item["output"],
        prompt_id=item["prompt_id"],
        model=item.get("model"),
        enqueued_at=item["enqueued_at"],
        queue_depth=depth,
    )


@router.post("/{item_id}", response_model=LabelResponse)
async def submit_label(
    item_id: str,
    body: LabelRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Submit a human verdict for an evaluation item.

    Writes the label to the database and updates the item's status.
    """
    # Validate the item exists
    stmt = select(EvalItem).where(EvalItem.id == item_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Idempotency check: don't double-label
    existing_label_stmt = select(Label).where(Label.eval_item_id == item_id)
    existing = await session.execute(existing_label_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Item {item_id} already has a label. Duplicate submission?"
        )

    # Validate edited verdict has corrected_output
    if body.verdict == "edited" and not body.corrected_output:
        raise HTTPException(
            status_code=422,
            detail="corrected_output is required when verdict is 'edited'"
        )

    # Write the label
    label = Label(
        eval_item_id=item_id,
        verdict=body.verdict,
        corrected_output=body.corrected_output,
        note=body.note,
        labeler_id=body.labeler_id,
    )
    session.add(label)

    # Update item status
    item.status = "labeled"

    # Emit OTEL span
    record_label(item_id, body.verdict, body.labeler_id or "anonymous")

    return LabelResponse(
        item_id=item_id,
        verdict=body.verdict,
        message="Label recorded. Thank you!",
    )


@router.post("/{item_id}/skip")
async def skip_item(
    item_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Skip this item — mark it as skipped in the DB.

    LESSON — When to skip:
    A labeler skips when they're unsure or the item is ambiguous.
    Skipped items could be re-queued for a second opinion, or
    accumulated for a calibration session.

    Here we just mark the status — you can build re-queue logic on top.
    """
    stmt = select(EvalItem).where(EvalItem.id == item_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    item.status = "skipped"
    return {"item_id": item_id, "status": "skipped"}
