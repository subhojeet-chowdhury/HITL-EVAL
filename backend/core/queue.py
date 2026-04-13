"""
backend/core/queue.py
─────────────────────
Redis queue abstraction layer.

LESSON — Why a queue at all?
─────────────────────────────
Without a queue, labeling is synchronous: your app produces an output,
someone labels it immediately, and results are processed. That's fine for
demos but breaks in production because:

  • LLM outputs arrive in bursts (10 in one second, then quiet for 5 minutes)
  • Human labelers work at human speed (~30 seconds per item)
  • You don't want your app to wait for a human

A queue *decouples* production from consumption. Your app pushes to the
left end of a Redis list with LPUSH. The labeler worker pops from the right
end with BRPOP. These can run at completely different rates.

LESSON — Redis data structure choice:
  - List  → simple FIFO queue (what we use here)
  - Stream → durable log with consumer groups (use if you have multiple labelers)
  - PubSub → fire-and-forget broadcast (wrong here — we need durability)

LESSON — BRPOP vs RPOP:
  RPOP returns None immediately if the list is empty.
  BRPOP blocks until an item arrives (or timeout expires).
  BRPOP is correct for a worker that should sleep when idle.
"""

import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as redis

from backend.core.config import settings


class EvalQueue:
    """
    Thin wrapper around Redis list operations.
    All methods are async — compatible with FastAPI's async event loop.
    """

    def __init__(self):
        # redis.asyncio.from_url parses the URL and returns a connection pool.
        # Connection pools are shared — don't create a new one per request.
        self._client: redis.Redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,  # return str, not bytes
        )

    async def enqueue(self, item: dict) -> str:
        """
        Push an evaluation item onto the queue.

        We assign a UUID here (not in the caller) so the queue is the
        single source of truth for item identity.

        Returns the item_id so the caller can track it.
        """
        item_id = str(uuid.uuid4())
        payload = {
            **item,
            "item_id": item_id,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        # LPUSH: insert at the LEFT (head) of the list
        # Combined with BRPOP (right), this gives us FIFO order
        await self._client.lpush(settings.queue_name, json.dumps(payload))
        return item_id

    async def dequeue(self, timeout: int = 5) -> dict | None:
        """
        Pop the oldest item from the queue.

        BRPOP blocks for `timeout` seconds, then returns None.
        The labeling endpoint calls this in a loop via long-polling.

        Returns None if the queue is empty after timeout.
        """
        # BRPOP returns a tuple: (list_name, value) or None on timeout
        result = await self._client.brpop(settings.queue_name, timeout=timeout)
        if result is None:
            return None
        _, raw = result
        return json.loads(raw)

    async def depth(self) -> int:
        """How many items are waiting to be labeled."""
        return await self._client.llen(settings.queue_name)

    async def ping(self) -> bool:
        """Health check — is Redis reachable?"""
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()


# Module-level singleton — FastAPI's lifespan will manage this
eval_queue = EvalQueue()
