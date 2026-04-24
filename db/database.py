"""
============================================================
db/database.py — Database Engine & Session Management
============================================================
Creates the SQLite engine, session factory, and provides:
  - get_db()      : FastAPI dependency (yields session)
  - init_db()     : Creates all tables on startup
  - seed_locations(): Seeds default Indian cities
"""

import os
import sys
from pathlib import Path
from loguru import logger
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.models import Base, Location

# ──────────────────────────────────────────────────────────
# Engine Setup
# ──────────────────────────────────────────────────────────

# Ensure the db/ directory exists
DB_DIR = Path(__file__).parent
DB_DIR.mkdir(parents=True, exist_ok=True)

# SQLite connection string → file stored in db/weather.db
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Required for SQLite + FastAPI
        "timeout": 30,
    },
    poolclass=StaticPool,       # Single connection pool for SQLite
    echo=settings.DEBUG,        # Print SQL queries when DEBUG=True
)


# Enable WAL mode for better concurrent reads in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ──────────────────────────────────────────────────────────
# Session Factory
# ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ──────────────────────────────────────────────────────────
# FastAPI Dependency: get_db
# ──────────────────────────────────────────────────────────
def get_db():
    """
    Yields a database session for FastAPI route handlers.
    Ensures the session is properly closed after each request.

    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────
# Table Initialization
# ──────────────────────────────────────────────────────────
def init_db():
    """
    Creates all database tables defined in models.py.
    Called once on application startup.
    Safe to call multiple times (CREATE IF NOT EXISTS).
    """
    logger.info("🗄️  Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.success("✅ Database tables ready.")
    seed_locations()


# ──────────────────────────────────────────────────────────
# Seed Default Locations
# ──────────────────────────────────────────────────────────
DEFAULT_LOCATIONS = [
    {"city": "Mumbai",    "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
    {"city": "Delhi",     "country": "India", "latitude": 28.6139, "longitude": 77.2090, "timezone": "Asia/Kolkata"},
    {"city": "Bangalore", "country": "India", "latitude": 12.9716, "longitude": 77.5946, "timezone": "Asia/Kolkata"},
    {"city": "Chennai",   "country": "India", "latitude": 13.0827, "longitude": 80.2707, "timezone": "Asia/Kolkata"},
    {"city": "Kolkata",   "country": "India", "latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"},
    {"city": "Hyderabad", "country": "India", "latitude": 17.3850, "longitude": 78.4867, "timezone": "Asia/Kolkata"},
    {"city": "Pune",      "country": "India", "latitude": 18.5204, "longitude": 73.8567, "timezone": "Asia/Kolkata"},
    {"city": "Ahmedabad", "country": "India", "latitude": 23.0225, "longitude": 72.5714, "timezone": "Asia/Kolkata"},
    {"city": "Jaipur",    "country": "India", "latitude": 26.9124, "longitude": 75.7873, "timezone": "Asia/Kolkata"},
    {"city": "Nagpur",    "country": "India", "latitude": 21.1458, "longitude": 79.0882, "timezone": "Asia/Kolkata"},
]


def seed_locations():
    """
    Inserts default Indian city locations into the database.
    Uses INSERT OR IGNORE pattern — safe to run multiple times.
    """
    db: Session = SessionLocal()
    try:
        existing_count = db.query(Location).count()
        if existing_count > 0:
            logger.info(f"📍 {existing_count} locations already seeded — skipping.")
            return

        logger.info("📍 Seeding default locations...")
        for loc_data in DEFAULT_LOCATIONS:
            loc = Location(**loc_data)
            db.add(loc)

        db.commit()
        logger.success(f"✅ Seeded {len(DEFAULT_LOCATIONS)} locations.")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to seed locations: {e}")
    finally:
        db.close()
