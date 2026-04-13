"""
backend/api/stats.py
────────────────────
Analytics and optimizer endpoints.

  GET  /stats/overview          → total counts across all prompts
  GET  /stats/prompt/{id}       → per-prompt breakdown
  POST /optimize/{prompt_id}    → trigger DSPy optimization
  GET  /optimize/{prompt_id}/history → prompt version history

LESSON — Why analytics matter for eval:
Without stats, you don't know:
  • Are most outputs good or bad? (→ is my prompt good or bad?)
  • Which prompt_id has the worst quality? (→ where to focus effort)
  • Did the last optimizer run actually help? (→ did quality improve?)

These queries aggregate your label data to answer those questions.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.queue import eval_queue
from backend.db.models import EvalItem, Label
from backend.db.session import get_db_session
from backend.optimizer.dspy_optimizer import HITLOptimizer

router = APIRouter(tags=["stats"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    total_items: int
    labeled_items: int
    pending_items: int
    skipped_items: int
    good_labels: int
    bad_labels: int
    edited_labels: int
    queue_depth: int
    label_rate_pct: float  # % of items labeled


class PromptStats(BaseModel):
    prompt_id: str
    total: int
    good: int
    bad: int
    edited: int
    pending: int
    good_rate_pct: float


class OptimizeRequest(BaseModel):
    base_prompt: str
    min_labels: int = settings.min_labels_for_optimization


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview(session: AsyncSession = Depends(get_db_session)):
    """Global stats across all prompts."""

    # Count items by status
    item_counts_stmt = (
        select(EvalItem.status, func.count(EvalItem.id))
        .group_by(EvalItem.status)
    )
    result = await session.execute(item_counts_stmt)
    item_counts = {row[0]: row[1] for row in result.all()}

    total = sum(item_counts.values())
    labeled = item_counts.get("labeled", 0)
    pending = item_counts.get("pending", 0)
    skipped = item_counts.get("skipped", 0)

    # Count labels by verdict
    label_counts_stmt = (
        select(Label.verdict, func.count(Label.id))
        .group_by(Label.verdict)
    )
    result = await session.execute(label_counts_stmt)
    label_counts = {row[0]: row[1] for row in result.all()}

    queue_depth = await eval_queue.depth()

    return OverviewStats(
        total_items=total,
        labeled_items=labeled,
        pending_items=pending,
        skipped_items=skipped,
        good_labels=label_counts.get("good", 0),
        bad_labels=label_counts.get("bad", 0),
        edited_labels=label_counts.get("edited", 0),
        queue_depth=queue_depth,
        label_rate_pct=round(labeled / total * 100, 1) if total > 0 else 0.0,
    )


@router.get("/stats/prompt/{prompt_id}", response_model=PromptStats)
async def get_prompt_stats(
    prompt_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Per-prompt statistics."""
    # Items with labels joined
    stmt = (
        select(EvalItem.status, Label.verdict, func.count(EvalItem.id))
        .outerjoin(Label, Label.eval_item_id == EvalItem.id)
        .where(EvalItem.prompt_id == prompt_id)
        .group_by(EvalItem.status, Label.verdict)
    )
    result = await session.execute(stmt)
    rows = result.all()

    good = bad = edited = pending = 0
    for status, verdict, count in rows:
        if status == "pending":
            pending += count
        elif verdict == "good":
            good += count
        elif verdict == "bad":
            bad += count
        elif verdict == "edited":
            edited += count

    total = good + bad + edited + pending
    labeled = good + bad + edited

    return PromptStats(
        prompt_id=prompt_id,
        total=total,
        good=good,
        bad=bad,
        edited=edited,
        pending=pending,
        good_rate_pct=round(good / labeled * 100, 1) if labeled > 0 else 0.0,
    )


@router.get("/stats/prompts")
async def list_prompts(session: AsyncSession = Depends(get_db_session)):
    """List all unique prompt_ids in the system."""
    stmt = select(EvalItem.prompt_id).distinct()
    result = await session.execute(stmt)
    return {"prompt_ids": [row[0] for row in result.all()]}


@router.post("/optimize/{prompt_id}")
async def run_optimizer(
    prompt_id: str,
    body: OptimizeRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Trigger the DSPy optimization loop for a given prompt.

    LESSON — When to call this:
    Call this after you've accumulated enough labels (default: 20).
    The optimizer reads your good labels, selects the best few-shot examples,
    and rewrites your prompt with them baked in.

    The response includes both the original and optimized prompt so you
    can inspect the diff before using it.
    """
    optimizer = HITLOptimizer(session)
    result = await optimizer.run(
        prompt_id=prompt_id,
        base_prompt=body.base_prompt,
        min_labels=body.min_labels,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "success": True,
        "prompt_id": result.prompt_id,
        "optimizer": result.optimizer_used,
        "examples_used": result.examples_used,
        "good_count": result.good_count,
        "bad_count": result.bad_count,
        "duration_ms": round(result.duration_ms, 1),
        "original_prompt": result.original_prompt,
        "optimized_prompt": result.optimized_prompt,
    }


@router.get("/optimize/{prompt_id}/history")
async def get_optimization_history(
    prompt_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Return all saved prompt versions for a given prompt_id."""
    optimizer = HITLOptimizer(session)
    history = await optimizer.get_prompt_history(prompt_id)
    return {"prompt_id": prompt_id, "versions": history}
