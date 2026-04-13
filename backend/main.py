"""
backend/main.py
───────────────
FastAPI application entrypoint.

LESSON — Application lifespan:
FastAPI's `lifespan` context manager runs code at startup and shutdown.
This is the right place for:
  • Creating DB tables
  • Initialising OTEL
  • Warming up connection pools

It replaces the old @app.on_event("startup") pattern.

LESSON — Static file serving:
We serve the compiled React frontend from FastAPI itself.
This means there's only ONE server to run, which is friendlier for
local dev and simple self-hosted deployments.

In production with high traffic, you'd put Nginx in front and let Nginx
serve the static files (it's much faster at that than Python).

LESSON — CORS:
Cross-Origin Resource Sharing headers tell browsers whether JavaScript
from one domain is allowed to call APIs on another domain.
In dev, we allow all origins (*).
In production, restrict to your actual frontend domain.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.ingest import router as ingest_router
from backend.api.label import router as label_router
from backend.api.stats import router as stats_router
from backend.core.config import settings
from backend.db.session import engine, init_db
from backend.observability.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup → runs before the first request.
    Shutdown → runs after the last request completes.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    print("🚀 Starting HITL Eval...")

    # Initialise database (create tables if they don't exist)
    await init_db()
    print("✅ Database ready")

    # Initialise OpenTelemetry
    setup_tracing(app=app, engine=engine.sync_engine)
    print(f"✅ Tracing ready (exporting to {settings.otel_exporter_endpoint})")

    print(f"✅ Redis queue: {settings.queue_name} @ {settings.redis_url}")
    print(f"📊 UI available at: http://localhost:8000")

    yield  # ← application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────
    print("👋 Shutting down HITL Eval...")
    await engine.dispose()


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_title,
    description="Human-in-the-Loop LLM evaluation with DSPy optimisation",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",   # Swagger UI
    redoc_url="/api/redoc", # ReDoc UI
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

# All API routes are prefixed with /api for clean separation from the UI
app.include_router(ingest_router, prefix="/api")
app.include_router(label_router, prefix="/api")
app.include_router(stats_router, prefix="/api")


# ── Static file serving (React frontend) ─────────────────────────────────────

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Serve compiled React app
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Catch-all route: serve index.html for any non-API path.

        LESSON — SPA routing:
        A React Single Page Application handles routing client-side.
        When you navigate to /label, React Router intercepts it.
        But if you refresh the page at /label, the browser asks the SERVER
        for /label — which doesn't exist as a file.

        The solution: return index.html for every non-API path.
        React Router then takes over and shows the right page.
        """
        index = FRONTEND_DIST / "index.html"
        return FileResponse(index)
else:
    @app.get("/", include_in_schema=False)
    async def dev_root():
        return {
            "message": "HITL Eval API is running!",
            "note": "React frontend not built yet. Run: cd frontend && npm run build",
            "api_docs": "/api/docs",
            "health": "/api/ingest/health",
        }
