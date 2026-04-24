"""
============================================================
api/app.py — FastAPI Application Entry Point
============================================================
Defines ALL API endpoints:

  GET  /                         → Health check
  GET  /api/locations            → List all locations
  POST /api/locations            → Add new location
  GET  /api/locations/{id}       → Location details
  GET  /api/weather/current/{id} → Current conditions
  GET  /api/forecast/hourly/{id} → Hourly forecast
  GET  /api/forecast/daily/{id}  → Daily forecast
  GET  /api/alerts               → All recent alerts
  GET  /api/alerts/{location_id} → Alerts for a city
  POST /api/ingest/{location_id} → Manual data refresh
  POST /api/ingest/all           → Refresh all locations
  POST /api/alerts/run/{id}      → Run alert engine manually
  GET  /api/summary              → Dashboard summary stats

Auto-docs available at: http://127.0.0.1:8000/docs
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session

# Project imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.database import get_db, init_db
from db.models import Location, WeatherHourly, WeatherDaily, AlertLog
from api.schemas import (
    LocationCreate, LocationResponse,
    HourlyWeatherResponse, DailyWeatherResponse,
    AlertResponse, IngestionResponse, StandardResponse,
    AlertSummary, CurrentWeatherResponse,
)
from src.ingestion import fetch_weather_for_location, fetch_all_locations
from src.rules import run_alert_engine, run_alert_engine_all_locations, interpret_weather_code


# ──────────────────────────────────────────────────────────
# App Initialization
# ──────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-grade Weather Forecast & Alert system "
        "powered by Open-Meteo API. Provides real-time weather, "
        "forecasts, and intelligent weather alerts for Indian cities."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Weather Alert System",
        "url": "https://github.com/your-username/weather-alert-app",
    },
    license_info={"name": "MIT"},
)

# ──────────────────────────────────────────────────────────
# CORS — Allow Streamlit frontend to connect
# ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, set to specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────
# Startup Event
# ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """
    Runs on application startup.
    Initializes database tables and seeds default locations.
    """
    logger.info("🚀 Weather Alert API starting up...")
    init_db()
    logger.success("✅ Application ready!")


# ══════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════

@app.get(
    "/",
    tags=["Health"],
    summary="API Health Check",
    response_description="Returns API status and version"
)
def root():
    """
    Health check endpoint. Use this to verify the API is running.
    """
    return {
        "status": "✅ Running",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Extended health check — also verifies DB connectivity."""
    location_count = db.query(Location).count()
    return {
        "status": "healthy",
        "database": "connected",
        "locations_seeded": location_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════
# LOCATIONS
# ══════════════════════════════════════════════════════════

@app.get(
    "/api/locations",
    response_model=List[LocationResponse],
    tags=["Locations"],
    summary="Get all tracked locations",
)
def get_locations(
    active_only: bool = Query(True, description="Return only active locations"),
    db: Session = Depends(get_db),
):
    """
    Returns all locations being tracked by the system.
    By default, only returns active (is_active=True) locations.
    """
    query = db.query(Location)
    if active_only:
        query = query.filter(Location.is_active == True)
    return query.order_by(Location.city).all()


@app.get(
    "/api/locations/{location_id}",
    response_model=LocationResponse,
    tags=["Locations"],
    summary="Get a specific location by ID",
)
def get_location(location_id: int, db: Session = Depends(get_db)):
    """Returns details for a single location."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail=f"Location ID {location_id} not found")
    return location


@app.post(
    "/api/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Locations"],
    summary="Add a new location to track",
)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    """
    Adds a new city/location to the tracking system.
    Duplicate cities with same lat/lon are rejected.
    """
    existing = (
        db.query(Location)
        .filter(
            Location.city == location.city,
            Location.latitude == location.latitude,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Location '{location.city}' already exists with ID {existing.id}"
        )

    new_loc = Location(**location.model_dump())
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    logger.info(f"📍 New location added: {new_loc.city} (ID={new_loc.id})")
    return new_loc


# ══════════════════════════════════════════════════════════
# CURRENT WEATHER
# ══════════════════════════════════════════════════════════

@app.get(
    "/api/weather/current/{location_id}",
    response_model=CurrentWeatherResponse,
    tags=["Weather"],
    summary="Get current weather conditions",
)
def get_current_weather(location_id: int, db: Session = Depends(get_db)):
    """
    Returns the most recent weather data for a location.
    'Current' = nearest hourly record to the present time.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=2)

    # Get the closest hourly record
    record = (
        db.query(WeatherHourly)
        .filter(
            WeatherHourly.location_id == location_id,
            WeatherHourly.forecast_time >= one_hour_ago,
        )
        .order_by(WeatherHourly.forecast_time)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="No recent weather data. Please run ingestion first: POST /api/ingest/{location_id}"
        )

    return CurrentWeatherResponse(
        city=location.city,
        latitude=location.latitude,
        longitude=location.longitude,
        timezone=location.timezone,
        temperature=record.temperature_2m,
        feels_like=record.apparent_temp,
        humidity=record.relative_humidity,
        wind_speed=record.wind_speed_10m,
        wind_gusts=record.wind_gusts_10m,
        uv_index=record.uv_index,
        cloud_cover=record.cloud_cover,
        precipitation_prob=record.precipitation_prob,
        weather_description=interpret_weather_code(record.weather_code),
        last_updated=record.forecast_time,
    )


# ══════════════════════════════════════════════════════════
# FORECASTS
# ══════════════════════════════════════════════════════════

@app.get(
    "/api/forecast/hourly/{location_id}",
    response_model=List[HourlyWeatherResponse],
    tags=["Forecast"],
    summary="Get hourly weather forecast",
)
def get_hourly_forecast(
    location_id: int,
    hours: int = Query(24, ge=1, le=168, description="Number of hours ahead (1–168)"),
    db: Session = Depends(get_db),
):
    """
    Returns hourly weather forecast for the next N hours.
    Default: next 24 hours. Maximum: 168 hours (7 days).
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    now = datetime.utcnow()
    end_time = now + timedelta(hours=hours)

    records = (
        db.query(WeatherHourly)
        .filter(
            WeatherHourly.location_id == location_id,
            WeatherHourly.forecast_time >= now,
            WeatherHourly.forecast_time <= end_time,
        )
        .order_by(WeatherHourly.forecast_time)
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No forecast data available. Run POST /api/ingest/{location_id} first."
        )

    # Enrich with weather description
    result = []
    for r in records:
        item = HourlyWeatherResponse.model_validate(r)
        item.weather_description = interpret_weather_code(r.weather_code)
        result.append(item)

    return result


@app.get(
    "/api/forecast/daily/{location_id}",
    response_model=List[DailyWeatherResponse],
    tags=["Forecast"],
    summary="Get daily weather forecast",
)
def get_daily_forecast(
    location_id: int,
    days: int = Query(7, ge=1, le=16, description="Number of days (1–16)"),
    db: Session = Depends(get_db),
):
    """
    Returns daily weather forecast for the next N days.
    Default: next 7 days. Maximum: 16 days.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today + timedelta(days=days)

    records = (
        db.query(WeatherDaily)
        .filter(
            WeatherDaily.location_id == location_id,
            WeatherDaily.forecast_date >= today,
            WeatherDaily.forecast_date <= end_date,
        )
        .order_by(WeatherDaily.forecast_date)
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No daily forecast data. Run POST /api/ingest/{location_id} first."
        )

    return records


# ══════════════════════════════════════════════════════════
# ALERTS
# ══════════════════════════════════════════════════════════

@app.get(
    "/api/alerts",
    response_model=List[AlertResponse],
    tags=["Alerts"],
    summary="Get all recent alerts across all locations",
)
def get_all_alerts(
    hours: int = Query(48, ge=1, le=720, description="Lookback window in hours"),
    active_only: bool = Query(True, description="Only return active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW/MEDIUM/HIGH/CRITICAL"),
    db: Session = Depends(get_db),
):
    """
    Returns all weather alerts generated in the last N hours.
    Can be filtered by severity and active status.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(AlertLog).filter(AlertLog.alert_time >= cutoff)

    if active_only:
        query = query.filter(AlertLog.is_active == True)

    if severity:
        query = query.filter(AlertLog.severity == severity.upper())

    return query.order_by(AlertLog.alert_time.desc()).all()


@app.get(
    "/api/alerts/{location_id}",
    response_model=List[AlertResponse],
    tags=["Alerts"],
    summary="Get alerts for a specific location",
)
def get_location_alerts(
    location_id: int,
    hours: int = Query(48, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """Returns all recent weather alerts for a specific city."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    alerts = (
        db.query(AlertLog)
        .filter(
            AlertLog.location_id == location_id,
            AlertLog.alert_time >= cutoff,
        )
        .order_by(AlertLog.alert_time.desc())
        .all()
    )

    return alerts


# ══════════════════════════════════════════════════════════
# INGESTION (Manual Triggers)
# ══════════════════════════════════════════════════════════

@app.post(
    "/api/ingest/{location_id}",
    response_model=IngestionResponse,
    tags=["Ingestion"],
    summary="Manually trigger weather data refresh for one location",
)
def ingest_location(location_id: int, db: Session = Depends(get_db)):
    """
    Triggers a manual weather data fetch for a specific location.
    Fetches data from Open-Meteo API and updates the database.
    Then automatically runs the alert engine.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    result = fetch_weather_for_location(location, db)

    # Auto-run alert engine after ingestion
    if result["status"] == "success":
        alerts = run_alert_engine(location_id, db)
        result["alerts_generated"] = len(alerts)

    return IngestionResponse(**result)


@app.post(
    "/api/ingest/all",
    response_model=List[IngestionResponse],
    tags=["Ingestion"],
    summary="Refresh weather data for ALL locations",
)
def ingest_all(db: Session = Depends(get_db)):
    """
    Triggers weather data refresh for all active locations.
    Then runs the alert engine for all locations.
    This is the same operation the APScheduler performs automatically.
    """
    results = fetch_all_locations(db)

    # Run alert engine for all locations
    alert_summary = run_alert_engine_all_locations(db)
    logger.info(f"🚨 Alert summary: {alert_summary}")

    return [IngestionResponse(**r) for r in results]


# ══════════════════════════════════════════════════════════
# ALERT ENGINE (Manual Trigger)
# ══════════════════════════════════════════════════════════

@app.post(
    "/api/alerts/run/{location_id}",
    response_model=List[AlertResponse],
    tags=["Alerts"],
    summary="Manually run alert engine for a location",
)
def trigger_alert_engine(location_id: int, db: Session = Depends(get_db)):
    """
    Manually runs the alert engine for a specific location.
    Evaluates current forecast data against all alert rules.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    alerts = run_alert_engine(location_id, db)
    return alerts


# ══════════════════════════════════════════════════════════
# DASHBOARD SUMMARY
# ══════════════════════════════════════════════════════════

@app.get(
    "/api/summary",
    tags=["Dashboard"],
    summary="Get dashboard summary statistics",
)
def get_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated statistics for the dashboard:
    - Location count
    - Alert counts by severity
    - Alert counts by type
    - Last ingestion time
    """
    total_locations = db.query(Location).filter(Location.is_active == True).count()

    cutoff = datetime.utcnow() - timedelta(hours=48)
    recent_alerts = (
        db.query(AlertLog)
        .filter(AlertLog.alert_time >= cutoff, AlertLog.is_active == True)
        .all()
    )

    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    type_counts = {"RAIN": 0, "HEAT": 0, "WIND": 0, "UV": 0}

    for alert in recent_alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        type_counts[alert.alert_type] = type_counts.get(alert.alert_type, 0) + 1

    last_ingest = (
        db.query(WeatherHourly)
        .order_by(WeatherHourly.created_at.desc())
        .first()
    )

    return {
        "total_locations": total_locations,
        "alerts_last_48h": len(recent_alerts),
        "by_severity": severity_counts,
        "by_type": type_counts,
        "last_data_refresh": last_ingest.created_at.isoformat() if last_ingest else None,
        "timestamp": datetime.utcnow().isoformat(),
    }
