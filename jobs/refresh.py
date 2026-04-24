"""
============================================================
jobs/refresh.py — APScheduler Background Job
============================================================
Sets up a background scheduler that:
  1. Fetches fresh weather data from Open-Meteo every N hours
  2. Runs the alert engine after each data refresh
  3. Sends notifications for new critical alerts

The scheduler runs as a separate process OR is embedded
into the FastAPI application using a lifespan event.

Usage:
    # Standalone (run as separate process):
    python jobs/refresh.py

    # Or integrated into main FastAPI app via lifespan

Schedule:
    Default: Every 3 hours (configurable via .env REFRESH_INTERVAL_MINUTES)
    First run: Immediately on startup
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.database import SessionLocal, init_db
from src.ingestion import fetch_all_locations
from src.rules import run_alert_engine_all_locations
from notify.alert import send_notification_for_new_alerts


# ──────────────────────────────────────────────────────────
# Job Listener (for logging scheduler events)
# ──────────────────────────────────────────────────────────

def job_listener(event):
    """Logs scheduler job execution results."""
    if event.exception:
        logger.error(f"❌ Scheduler job FAILED: {event.job_id} — {event.exception}")
    else:
        logger.success(f"✅ Scheduler job COMPLETED: {event.job_id}")


# ──────────────────────────────────────────────────────────
# The Main Refresh Job
# ──────────────────────────────────────────────────────────

def weather_refresh_job():
    """
    The core scheduled task.

    Steps:
      1. Open a new DB session
      2. Fetch fresh weather for all active locations
      3. Run alert engine to evaluate new conditions
      4. Send notifications for any new alerts
      5. Close DB session

    This function is called by APScheduler on the configured interval.
    """
    logger.info(f"⏰ Scheduled weather refresh started at {datetime.utcnow().isoformat()} UTC")

    db = SessionLocal()
    try:
        # Step 1: Ingest fresh weather data
        logger.info("📡 Step 1/3: Fetching weather data from Open-Meteo...")
        ingestion_results = fetch_all_locations(db)

        success_count = sum(1 for r in ingestion_results if r["status"] == "success")
        logger.info(f"  └── Ingestion: {success_count}/{len(ingestion_results)} locations updated")

        # Step 2: Run alert engine
        logger.info("🔍 Step 2/3: Running alert engine...")
        alert_summary = run_alert_engine_all_locations(db)
        total_new_alerts = sum(alert_summary.values())
        logger.info(f"  └── Alerts: {total_new_alerts} new alerts generated")

        # Step 3: Send notifications
        logger.info("📬 Step 3/3: Sending notifications...")
        send_notification_for_new_alerts(db)

        logger.success(
            f"✅ Weather refresh complete. "
            f"Locations: {success_count}, "
            f"New alerts: {total_new_alerts}"
        )

    except Exception as e:
        logger.error(f"❌ Weather refresh job failed: {e}")
        raise

    finally:
        db.close()


# ──────────────────────────────────────────────────────────
# Scheduler Setup
# ──────────────────────────────────────────────────────────

def create_scheduler() -> BackgroundScheduler:
    """
    Creates and configures the APScheduler instance.

    Returns:
        Configured BackgroundScheduler (not yet started)
    """
    scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,          # Merge missed jobs into one
            "max_instances": 1,         # Only one instance at a time
            "misfire_grace_time": 60,   # Allow 60s late execution
        },
        timezone="UTC",
    )

    # Add the refresh job
    scheduler.add_job(
        func=weather_refresh_job,
        trigger=IntervalTrigger(
            minutes=settings.REFRESH_INTERVAL_MINUTES,
            start_date=datetime.utcnow(),  # First run immediately
        ),
        id="weather_refresh",
        name="Weather Data Refresh",
        replace_existing=True,
    )

    # Add event listener for logging
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    logger.info(
        f"⏱️  Scheduler configured: "
        f"refresh every {settings.REFRESH_INTERVAL_MINUTES} minutes"
    )

    return scheduler


# ──────────────────────────────────────────────────────────
# Standalone Entry Point
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run the scheduler as a standalone background process.

    Terminal: python jobs/refresh.py
    """
    logger.info("🚀 Starting Weather Refresh Scheduler (standalone mode)...")

    # Initialize DB
    init_db()

    # Create and start scheduler
    scheduler = create_scheduler()
    scheduler.start()

    logger.info(
        f"✅ Scheduler running. "
        f"Next refresh in {settings.REFRESH_INTERVAL_MINUTES} minutes.\n"
        f"Press Ctrl+C to stop."
    )

    try:
        # Keep the process alive
        while True:
            time.sleep(60)

    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler stopped by user.")
        scheduler.shutdown(wait=False)
        logger.info("👋 Goodbye!")
