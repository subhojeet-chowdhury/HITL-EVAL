"""
backend/core/config.py
─────────────────────
Central configuration using pydantic-settings.

LESSON: pydantic-settings reads values in this priority order:
  1. Environment variables (highest priority)
  2. .env file
  3. Default values defined below

This means you NEVER hard-code secrets. In dev you use a .env file;
in production you set real env vars. Same code, different behaviour.

Usage anywhere in the codebase:
    from backend.core.config import settings
    print(settings.redis_url)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Redis ──────────────────────────────────────────────────────────────
    # Redis is used as the queue. LPUSH to add, BRPOP to consume.
    redis_url: str = "redis://localhost:6379"
    queue_name: str = "hitl:eval:queue"

    # ── Database ───────────────────────────────────────────────────────────
    # SQLite by default (zero setup). Swap to Postgres with:
    #   DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
    database_url: str = "sqlite+aiosqlite:///./hitl_eval.db"

    # ── OpenTelemetry ──────────────────────────────────────────────────────
    # OTEL collector endpoint. Jaeger's default gRPC port is 4317.
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "hitl-eval"

    # ── Optimiser ──────────────────────────────────────────────────────────
    # Don't run the optimiser until we have enough labels to be meaningful.
    min_labels_for_optimization: int = 20

    # ── App ────────────────────────────────────────────────────────────────
    app_title: str = "HITL Eval"
    debug: bool = False

    # Tell pydantic-settings to also read from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton — import this everywhere
settings = Settings()
