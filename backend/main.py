"""
CardioXAI — FastAPI Backend Server

Sprint 1(A): Basic server setup and project structure.
Sprint 1(B): JWT authentication and security.
Sprint 1(C): Clinical and ECG data upload APIs.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from config import settings
from database import init_indexes
from upload import router as upload_router

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"


# ── Lifespan (startup / shutdown) ────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on server startup and shutdown."""
    # — Startup —
    init_indexes()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ {settings.APP_NAME} v{settings.APP_VERSION} is running")
    print(f"✓ Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
    yield
    # — Shutdown —
    print("✗ Server shutting down")


# ── App ──────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(upload_router)


# ── Health Check ─────────────────────────────────────────────────


@app.get("/health", tags=["System"])
def health_check():
    """Basic health check — confirms the server is up."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["System"])
def root():
    """Root endpoint — API info."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
