"""
backend/api/ingest.py
─────────────────────
POST /ingest — receives LLM outputs and pushes them to the queue.

LESSON — This is the "producer" side of the queue.
Your application (or a script) calls this endpoint after getting a
response from an LLM. The endpoint:
  1. Validates the payload (Pydantic)
  2. Saves the raw item to the database (for durability)
  3. Pushes it to the Redis queue (for async processing)
  4. Returns the item_id immediately (non-blocking for your app)

LESSON — Why save to DB *and* queue?
Redis is a cache. If Redis crashes without persistence, you lose the queue.
The DB is the system of record. The queue is the work distribution layer.
On startup, you could replay unprocessed DB items back into the queue.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.queue import eval_queue
from backend.db.models import EvalItem
from backend.db.session import get_db_session
from backend.observability.tracing import record_ingest

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── Request / Response schemas ────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """
    LESSON — Pydantic models as API contracts.
    
    Pydantic validates incoming JSON automatically. If a required field is
    missing or has the wrong type, FastAPI returns a 422 with clear error
    messages — before your code even runs.

    `Field(...)` means required. `Field(None)` means optional.
    `Field(..., description="...")` adds documentation to the auto-generated
    Swagger UI at /docs.
    """
    prompt: str = Field(..., description="The prompt sent to the LLM")
    output: str = Field(..., description="The LLM's response")
    prompt_id: str = Field(..., description="Logical prompt identifier, e.g. 'summariser_v3'")
    model: str | None = Field(None, description="Model name, e.g. 'gpt-4o'")
    metadata: dict | None = Field(None, description="Arbitrary key-value metadata")


class IngestResponse(BaseModel):
    item_id: str
    queue_depth: int
    message: str


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_item(
    body: IngestRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Receive an LLM output and enqueue it for human labeling.

    This is the entry point for your application. Call this after every
    LLM response you want to evaluate.
    """
    # 1. Push to Redis queue first (fast, non-blocking)
    payload = {
        "prompt": body.prompt,
        "output": body.output,
        "prompt_id": body.prompt_id,
        "model": body.model,
    }
    item_id = await eval_queue.enqueue(payload)

    # 2. Save to database for durability
    #    If Redis goes down, we still have the record.
    db_item = EvalItem(
        id=item_id,
        prompt=body.prompt,
        output=body.output,
        prompt_id=body.prompt_id,
        model=body.model,
        metadata_json=json.dumps(body.metadata) if body.metadata else None,
        status="pending",
    )
    session.add(db_item)
    # session commit happens automatically via the get_db_session context manager

    # 3. Emit an OTEL span
    record_ingest(item_id, body.prompt_id, body.model or "unknown")

    # 4. Get current queue depth for the response
    depth = await eval_queue.depth()

    return IngestResponse(
        item_id=item_id,
        queue_depth=depth,
        message="Item queued for evaluation",
    )


@router.get("/health")
async def health_check():
    """Quick health check — is Redis reachable?"""
    redis_ok = await eval_queue.ping()
    if not redis_ok:
        raise HTTPException(
            status_code=503,
            detail="Redis is not reachable. Check your REDIS_URL."
        )
    return {"status": "ok", "redis": "connected"}
