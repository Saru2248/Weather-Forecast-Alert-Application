"""
============================================================
main.py — Unified Application Entry Point
============================================================
Starts FastAPI + APScheduler in a single process.

Usage:
    python main.py
    # OR
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from db.database import init_db
from api.app import app as weather_app
from jobs.refresh import create_scheduler, weather_refresh_job

# Configure loguru
logger.add(
    "logs/weather_app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# ── Lifespan: startup + shutdown ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("=" * 60)
    logger.info(f"🚀  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    init_db()

    # Start background scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.success("⏰  Background scheduler started.")

    # Run first ingestion immediately
    logger.info("📡  Running initial weather fetch...")
    try:
        weather_refresh_job()
    except Exception as e:
        logger.warning(f"Initial fetch warning (non-fatal): {e}")

    yield  # App runs here

    # SHUTDOWN
    logger.info("🛑  Shutting down scheduler...")
    scheduler.shutdown(wait=False)
    logger.info("👋  Goodbye!")


# Attach lifespan to the imported app
weather_app.router.lifespan_context = lifespan
app = weather_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
