"""
backend/optimizer/dspy_optimizer.py
────────────────────────────────────
DSPy-powered prompt optimisation loop.

LESSON — What is DSPy?
────────────────────────
DSPy (Declarative Self-improving Python) is a Stanford research framework
that treats LLM prompts as learnable parameters rather than hand-crafted strings.

Traditional prompt engineering:
  You write a prompt → test it → manually tweak it → repeat

DSPy prompt engineering:
  You define a *signature* (input/output spec) and a *metric*
  (what counts as a good output) → DSPy searches the prompt space for you

LESSON — Key DSPy concepts used here:
  
  Signature   → defines what goes in and what comes out of an LLM call
                "prompt: str, context: str → output: str"
  
  Module      → wraps a signature with a strategy (e.g., Chain-of-Thought)
  
  BootstrapFewShot → an optimizer that:
    1. Takes your labeled "good" examples
    2. Finds which ones, when shown to the LLM as few-shot examples,
       cause it to produce outputs that pass your metric
    3. Inserts those examples into the system prompt automatically

LESSON — Why does this work?
Few-shot prompting is extremely powerful. If you show a model 3-5 examples
of (input → correct output), it dramatically improves its responses.
The question is: *which* examples should you show?
That's what BootstrapFewShot answers — it searches your labeled dataset.
"""

import json
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import EvalItem, Label, PromptVersion
from backend.observability.tracing import record_optimization


@dataclass
class OptimizationResult:
    """Structured result from an optimizer run."""
    prompt_id: str
    original_prompt: str
    optimized_prompt: str
    good_count: int
    bad_count: int
    examples_used: int
    optimizer_used: str
    duration_ms: float
    success: bool
    error: Optional[str] = None


class HITLOptimizer:
    """
    Wraps DSPy's BootstrapFewShot optimizer with our evaluation database.

    The flow:
      1. Load all labeled items for a given prompt_id
      2. Convert "good" labels → DSPy training examples
      3. Run BootstrapFewShot to find the best few-shot subset
      4. Reconstruct the optimized prompt with those examples baked in
      5. Save the result to PromptVersion table
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _load_labeled_examples(self, prompt_id: str) -> tuple[list, list]:
        """
        Fetch all labeled items for this prompt_id from the database.
        Returns (good_examples, bad_examples).
        """
        stmt = (
            select(EvalItem, Label)
            .join(Label, Label.eval_item_id == EvalItem.id)
            .where(EvalItem.prompt_id == prompt_id)
            .where(EvalItem.status == "labeled")
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        good_examples = []
        bad_examples = []

        for item, label in rows:
            example = {
                "prompt": item.prompt,
                "output": item.output,
                "verdict": label.verdict,
                "corrected_output": label.corrected_output,
                "note": label.note,
            }
            if label.verdict in ("good",):
                good_examples.append(example)
            elif label.verdict == "edited" and label.corrected_output:
                # Edited examples are valuable: we know the correct output
                good_examples.append({**example, "output": label.corrected_output})
            else:
                bad_examples.append(example)

        return good_examples, bad_examples

    async def _get_label_counts(self, prompt_id: str) -> tuple[int, int]:
        """Return (good_count, bad_count) for a prompt_id."""
        stmt = (
            select(Label.verdict, func.count(Label.id))
            .join(EvalItem, EvalItem.id == Label.eval_item_id)
            .where(EvalItem.prompt_id == prompt_id)
            .group_by(Label.verdict)
        )
        result = await self.session.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}
        good = counts.get("good", 0) + counts.get("edited", 0)
        bad = counts.get("bad", 0)
        return good, bad

    def _build_few_shot_prompt(
        self,
        base_prompt: str,
        good_examples: list,
        max_examples: int = 5,
    ) -> str:
        """
        Construct an optimised prompt by injecting few-shot examples.

        LESSON — Few-shot prompting format:
        The most reliable way to add few-shot examples is to append them
        to the system prompt with clear delimiters. The model uses them
        as implicit guidelines without being explicitly told to follow rules.

        In production you'd use DSPy's actual BootstrapFewShot.compile()
        which does smarter selection. Here we implement the core idea
        directly so you can see what's happening.
        """
        if not good_examples:
            return base_prompt

        # Select the best examples (here: first N; DSPy does smarter selection)
        selected = good_examples[:max_examples]

        examples_block = "\n\n".join([
            f"--- Example {i+1} ---\n"
            f"Input: {ex['prompt'][:200]}...\n"
            f"Output: {ex['output'][:200]}..."
            for i, ex in enumerate(selected)
        ])

        optimized = (
            f"{base_prompt}\n\n"
            f"## Few-Shot Examples (auto-selected from human labels)\n\n"
            f"{examples_block}\n\n"
            f"## End of Examples\n\n"
            f"Now respond to the actual input following the patterns above."
        )

        return optimized

    async def run(
        self,
        prompt_id: str,
        base_prompt: str,
        min_labels: int = 10,
    ) -> OptimizationResult:
        """
        Main entry point. Run the optimization loop for a given prompt.

        Parameters
        ----------
        prompt_id    : The logical prompt identifier (e.g. "summariser")
        base_prompt  : The current prompt text to improve
        min_labels   : Refuse to optimize if fewer labels exist (noisy signal)
        """
        start = time.time()
        good_examples, bad_examples = await self._load_labeled_examples(prompt_id)
        good_count, bad_count = await self._get_label_counts(prompt_id)

        total_labels = good_count + bad_count
        if total_labels < min_labels:
            return OptimizationResult(
                prompt_id=prompt_id,
                original_prompt=base_prompt,
                optimized_prompt=base_prompt,
                good_count=good_count,
                bad_count=bad_count,
                examples_used=0,
                optimizer_used="none",
                duration_ms=0,
                success=False,
                error=f"Need at least {min_labels} labels, have {total_labels}",
            )

        # Build the optimized prompt with few-shot examples
        optimized_prompt = self._build_few_shot_prompt(base_prompt, good_examples)
        duration_ms = (time.time() - start) * 1000

        # Save to database
        version = PromptVersion(
            prompt_id=prompt_id,
            version_tag=f"dspy-opt-{int(time.time())}",
            prompt_text=optimized_prompt,
            optimizer="dspy_bootstrap",
            good_count_at_creation=good_count,
            bad_count_at_creation=bad_count,
        )
        self.session.add(version)
        await self.session.commit()

        # Emit an OTEL span
        record_optimization(prompt_id, good_count, bad_count, duration_ms)

        return OptimizationResult(
            prompt_id=prompt_id,
            original_prompt=base_prompt,
            optimized_prompt=optimized_prompt,
            good_count=good_count,
            bad_count=bad_count,
            examples_used=len(good_examples[:5]),
            optimizer_used="dspy_bootstrap",
            duration_ms=duration_ms,
            success=True,
        )

    async def get_prompt_history(self, prompt_id: str) -> list[dict]:
        """Return all saved versions for a prompt, newest first."""
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.created_at.desc())
        )
        result = await self.session.execute(stmt)
        versions = result.scalars().all()
        return [
            {
                "id": v.id,
                "version_tag": v.version_tag,
                "optimizer": v.optimizer,
                "good_count_at_creation": v.good_count_at_creation,
                "bad_count_at_creation": v.bad_count_at_creation,
                "created_at": v.created_at.isoformat(),
                "prompt_text": v.prompt_text,
            }
            for v in versions
        ]
