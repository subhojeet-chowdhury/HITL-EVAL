"""
backend/db/models.py
────────────────────
SQLAlchemy ORM models — the shape of our database.

LESSON — What is an ORM?
─────────────────────────
An ORM (Object-Relational Mapper) lets you work with databases using Python
classes instead of raw SQL. SQLAlchemy is the standard Python ORM.

  Without ORM:  cursor.execute("INSERT INTO eval_items ...")
  With ORM:     session.add(EvalItem(prompt="...", output="..."))

SQLAlchemy 2.0 uses a "declarative" style with type annotations.
The `Mapped[str]` annotation tells SQLAlchemy both the Python type AND
generates the correct SQL column type.

LESSON — Why separate tables?
──────────────────────────────
EvalItem    → one row per LLM output that enters the system
Label       → one row per human judgment (linked to EvalItem)
PromptVersion → one row per prompt version tracked

We separate them because:
  • One item can receive multiple labels (disagreement analysis)
  • Prompt versions are independent of individual items
  • It lets us query: "what fraction of v3 outputs were labeled Bad?"
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """All models inherit from this. DeclarativeBase wires up the metadata."""
    pass


class EvalItem(Base):
    """
    Represents one LLM output that has entered the evaluation pipeline.

    LESSON — Indexes:
    We index `prompt_id` because we frequently query "all items for prompt X".
    We index `status` because the UI queries "all unlabeled items".
    Indexes speed up reads at the cost of slightly slower writes — acceptable here.
    """
    __tablename__ = "eval_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID

    # The prompt that generated this output
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # The LLM's actual response
    output: Mapped[str] = mapped_column(Text, nullable=False)

    # Which logical prompt are we tracking? e.g. "summariser_v3"
    # This is how you group items for the optimiser.
    prompt_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Which model produced this? e.g. "gpt-4o", "claude-3-opus"
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Arbitrary JSON metadata from the caller (user_id, session_id, etc.)
    # Stored as a string; parse it in application code.
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # "pending" → waiting for a label
    # "labeled" → a human has judged it
    # "skipped" → labeler chose to skip
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # One item can have many labels (if you want inter-annotator agreement)
    labels: Mapped[list["Label"]] = relationship("Label", back_populates="eval_item")


class Label(Base):
    """
    A human judgment on an EvalItem.

    LESSON — The label is the gold.
    Every (prompt, output, label) triple you collect is training data.
    Accumulate enough of these and you can:
      1. Fine-tune a model
      2. Train a reward model
      3. Drive DSPy optimisation (what we do here)
    """
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    eval_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("eval_items.id"), nullable=False, index=True
    )

    # "good" | "bad" | "edited"
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)

    # If verdict == "edited", this holds the corrected output
    corrected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Free-text note from the labeler ("wrong tone", "hallucinated facts")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who labeled it? Useful when you have multiple labelers
    labeler_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    eval_item: Mapped["EvalItem"] = relationship("EvalItem", back_populates="labels")


class PromptVersion(Base):
    """
    Tracks the history of prompt rewrites produced by the optimiser.

    LESSON — Why store prompt versions?
    You need to be able to answer: "Was prompt v4 better than v3?"
    That requires knowing what each version actually said, and what
    the label distribution looked like when it was active.
    """
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Logical prompt identifier (matches EvalItem.prompt_id)
    prompt_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # e.g. "v1", "v2", "dspy-opt-20240415"
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)

    # The actual prompt text
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optimiser that produced this version: "manual" | "dspy_bootstrap" | "dspy_mipro"
    optimizer: Mapped[str] = mapped_column(String(64), default="manual")

    # Snapshot of label counts when this version was created
    good_count_at_creation: Mapped[int] = mapped_column(default=0)
    bad_count_at_creation: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
