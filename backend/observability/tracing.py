"""
backend/observability/tracing.py
─────────────────────────────────
OpenTelemetry setup and span helpers.

LESSON — What is OpenTelemetry?
────────────────────────────────
OpenTelemetry (OTEL) is the open standard for observability. It defines
how to emit:
  • Traces  → records of what happened (and how long each step took)
  • Metrics → numeric measurements (queue depth, label rate, etc.)
  • Logs    → structured log events (not used here, use your logger)

A **trace** is a tree of **spans**. Each span represents one operation.
In our system, a full evaluation trace looks like:

  ┌─ ingest_item (span) ──────────────────────────────────────────────┐
  │  enqueued_at=..., prompt_id=..., model=...                        │
  │                                                                   │
  │  ┌─ redis_lpush (child span) ──────────────────────────────────┐  │
  │  │  duration=0.3ms                                             │  │
  │  └──────────────────────────────────────────────────────────────┘  │
  └───────────────────────────────────────────────────────────────────┘

  ┌─ submit_label (span) ─────────────────────────────────────────────┐
  │  item_id=..., verdict=good, labeler_id=...                        │
  └───────────────────────────────────────────────────────────────────┘

LESSON — Why does this matter in production?
You can answer questions like:
  • "Why did labeling slow down yesterday?" (look at span durations)
  • "Which prompt_id has the most bad labels?" (filter traces by attribute)
  • "How long does the optimizer take to run?" (optimizer span duration)

LESSON — OTEL vs logging:
Logs tell you *what* happened. Traces tell you *where* in the flow it
happened, *how long* it took, and how operations relate to each other.
Use both.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes

from backend.core.config import settings


def setup_tracing(app=None, engine=None):
    """
    Initialise the OpenTelemetry SDK.

    Call this once at application startup (in the lifespan handler).

    Parameters
    ----------
    app    : FastAPI app instance (for auto-instrumentation)
    engine : SQLAlchemy engine (for auto-instrumentation)
    """

    # Resource describes *what* is generating the traces.
    # This shows up as the service name in Jaeger/Honeycomb.
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.otel_service_name,
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
    })

    # TracerProvider is the SDK's core — it manages trace lifecycle.
    provider = TracerProvider(resource=resource)

    # ── Exporters ─────────────────────────────────────────────────────────
    # An exporter sends completed spans somewhere.
    # We add two:

    # 1. OTLP exporter — sends to Jaeger, Grafana Tempo, Honeycomb, etc.
    #    This is the "real" exporter for production.
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint,
            insecure=True,  # no TLS for local dev
        )
        # BatchSpanProcessor buffers spans and sends them in batches.
        # More efficient than sending one span per HTTP request.
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception:
        # If no OTEL collector is running, fall back gracefully
        pass

    # 2. Console exporter — prints spans to stdout in dev mode.
    #    Remove or gate this in production.
    if settings.debug:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Register this provider as the global default.
    # After this call, `trace.get_tracer(...)` uses our provider.
    trace.set_tracer_provider(provider)

    # ── Auto-instrumentation ───────────────────────────────────────────────
    # These instrumentors monkey-patch libraries to emit spans automatically.
    # FastAPIInstrumentor adds a span for every HTTP request.
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    # SQLAlchemyInstrumentor adds spans for every SQL query.
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)

    return provider


def get_tracer() -> trace.Tracer:
    """
    Get a tracer for manual span creation.

    Usage:
        tracer = get_tracer()
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("key", "value")
            do_work()
    """
    return trace.get_tracer("hitl_eval")


# ── Span helpers ──────────────────────────────────────────────────────────────
# These wrap common operations so routes don't have to know OTEL internals.

def record_ingest(item_id: str, prompt_id: str, model: str):
    """Emit a span event when an item enters the queue."""
    tracer = get_tracer()
    with tracer.start_as_current_span("item.ingested") as span:
        span.set_attribute("item.id", item_id)
        span.set_attribute("prompt.id", prompt_id)
        span.set_attribute("model", model or "unknown")


def record_label(item_id: str, verdict: str, labeler_id: str):
    """Emit a span event when a human submits a label."""
    tracer = get_tracer()
    with tracer.start_as_current_span("item.labeled") as span:
        span.set_attribute("item.id", item_id)
        span.set_attribute("label.verdict", verdict)
        span.set_attribute("labeler.id", labeler_id or "anonymous")


def record_optimization(prompt_id: str, good_count: int, bad_count: int, duration_ms: float):
    """Emit a span event when the optimiser runs."""
    tracer = get_tracer()
    with tracer.start_as_current_span("optimizer.run") as span:
        span.set_attribute("prompt.id", prompt_id)
        span.set_attribute("labels.good", good_count)
        span.set_attribute("labels.bad", bad_count)
        span.set_attribute("duration_ms", duration_ms)
