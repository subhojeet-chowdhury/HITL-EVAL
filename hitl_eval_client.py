"""
hitl_eval_client.py
────────────────────
Python SDK — drop this file into your project to send LLM outputs to HITL Eval.

LESSON — Why a thin client SDK?
Your application shouldn't need to know about HTTP, JSON serialization, or
error handling every time it wants to enqueue an evaluation item.
A thin SDK wraps all that behind a clean interface:

    client = HITLClient()
    client.enqueue(prompt=..., output=..., prompt_id=...)

This is also how you'd structure a real OSS SDK — the user installs the
package, imports the client, and calls methods. The transport is hidden.

Usage:
    # Sync (default):
    from hitl_eval_client import HITLClient
    client = HITLClient(base_url="http://localhost:8000")
    client.enqueue(prompt="...", output="...", prompt_id="my_prompt")

    # Async:
    from hitl_eval_client import AsyncHITLClient
    client = AsyncHITLClient(base_url="http://localhost:8000")
    await client.enqueue(...)
"""

from __future__ import annotations

from typing import Any

import httpx


class HITLClient:
    """
    Synchronous HITL Eval client.
    Use this in regular Python code (scripts, Flask apps, etc.)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def enqueue(
        self,
        prompt: str,
        output: str,
        prompt_id: str,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Send an LLM output to the evaluation queue.

        Parameters
        ----------
        prompt     : The prompt that was sent to the LLM
        output     : The LLM's response (what you want evaluated)
        prompt_id  : Logical prompt identifier for grouping (e.g. "summariser_v3")
        model      : Model name (e.g. "gpt-4o", "claude-3-5-sonnet")
        metadata   : Any extra data to attach (user_id, session_id, etc.)

        Returns the server response with item_id and queue_depth.
        """
        response = self._client.post(
            "/api/ingest/",
            json={
                "prompt": prompt,
                "output": output,
                "prompt_id": prompt_id,
                "model": model,
                "metadata": metadata,
            },
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> dict:
        """Fetch overview statistics."""
        response = self._client.get("/api/stats/overview")
        response.raise_for_status()
        return response.json()

    def health(self) -> bool:
        """Return True if the server is healthy."""
        try:
            r = self._client.get("/api/ingest/health")
            return r.status_code == 200
        except Exception:
            return False

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncHITLClient:
    """
    Async HITL Eval client.
    Use this in async Python code (FastAPI apps, async scripts, etc.)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def enqueue(
        self,
        prompt: str,
        output: str,
        prompt_id: str,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Async version of enqueue."""
        response = await self._client.post(
            "/api/ingest/",
            json={
                "prompt": prompt,
                "output": output,
                "prompt_id": prompt_id,
                "model": model,
                "metadata": metadata,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
