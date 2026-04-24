"""
============================================================
src/ingestion.py — Weather Data Ingestion Module
============================================================
Responsible for:
  1. Fetching weather data from Open-Meteo API (free, no key)
  2. Validating and parsing the JSON response
  3. Storing raw JSON in weather_raw table
  4. Parsing and upserting hourly data into weather_hourly
  5. Parsing and upserting daily data into weather_daily

Open-Meteo API Docs: https://open-meteo.com/en/docs
No API key required. Rate limit: generous for free usage.

Workflow:
  fetch_weather_for_location(location, db)
    └─► call_open_meteo_api(lat, lon, timezone)
    └─► save_raw_response(...)
    └─► parse_and_store_hourly(...)
    └─► parse_and_store_daily(...)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# Project imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.models import Location, WeatherRaw, WeatherHourly, WeatherDaily


# ──────────────────────────────────────────────────────────
# Open-Meteo API Parameters
# ──────────────────────────────────────────────────────────

HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "uv_index",
    "cloud_cover",
    "visibility",
    "weathercode",
    "surface_pressure",
]

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "uv_index_max",
    "sunrise",
    "sunset",
    "weathercode",
]

# ──────────────────────────────────────────────────────────
# API CALL
# ──────────────────────────────────────────────────────────

def call_open_meteo_api(
    latitude: float,
    longitude: float,
    timezone: str = "Asia/Kolkata",
    forecast_days: int = 7,
) -> dict:
    """
    Calls the Open-Meteo free weather API.

    Parameters:
        latitude      : Location latitude
        longitude     : Location longitude
        timezone      : IANA timezone string (e.g. "Asia/Kolkata")
        forecast_days : Number of forecast days (1–16)

    Returns:
        Parsed JSON dict from Open-Meteo API

    Raises:
        httpx.HTTPStatusError : On non-200 API response
        httpx.TimeoutException: On connection timeout
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "forecast_days": forecast_days,
        "hourly": ",".join(HOURLY_VARIABLES),
        "daily": ",".join(DAILY_VARIABLES),
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }

    logger.info(f"🌐 Calling Open-Meteo API for ({latitude}, {longitude})...")

    with httpx.Client(timeout=30.0) as client:
        response = client.get(settings.OPEN_METEO_BASE_URL, params=params)
        response.raise_for_status()

    data = response.json()
    logger.success(f"✅ API response received. Keys: {list(data.keys())}")
    return data


# ──────────────────────────────────────────────────────────
# SAVE RAW RESPONSE
# ──────────────────────────────────────────────────────────

def save_raw_response(
    db: Session,
    location_id: int,
    raw_data: dict,
    status: str = "success",
    error_msg: Optional[str] = None,
) -> WeatherRaw:
    """
    Persists the raw API JSON response to weather_raw table.
    This ensures we have a full audit trail of all API calls.

    Parameters:
        db          : SQLAlchemy session
        location_id : FK to locations table
        raw_data    : Parsed JSON from API
        status      : "success" or "error"
        error_msg   : Error description if status="error"

    Returns:
        WeatherRaw ORM instance
    """
    raw_record = WeatherRaw(
        location_id=location_id,
        api_source="open-meteo",
        raw_json=json.dumps(raw_data),
        status=status,
        error_msg=error_msg,
        fetched_at=datetime.utcnow(),
    )
    db.add(raw_record)
    db.commit()
    db.refresh(raw_record)
    logger.info(f"💾 Raw response saved (id={raw_record.id})")
    return raw_record


# ──────────────────────────────────────────────────────────
# PARSE & STORE HOURLY DATA
# ──────────────────────────────────────────────────────────

def parse_and_store_hourly(
    db: Session,
    location_id: int,
    hourly_data: dict,
) -> int:
    """
    Parses the 'hourly' section of Open-Meteo API response and
    upserts records into weather_hourly table.

    The hourly data is returned as parallel arrays:
      hourly.time           = ["2024-01-01T00:00", ...]
      hourly.temperature_2m = [25.3, 24.1, ...]
      ...

    We zip these arrays into individual row records.

    Parameters:
        db          : SQLAlchemy session
        location_id : FK to locations table
        hourly_data : The 'hourly' dict from API response

    Returns:
        Number of records upserted
    """
    times = hourly_data.get("time", [])
    if not times:
        logger.warning("⚠️  No hourly time entries found in API response.")
        return 0

    inserted = 0

    for i, time_str in enumerate(times):
        try:
            forecast_time = datetime.fromisoformat(time_str)

            def safe_get(key: str):
                """Safely extract value from parallel array."""
                arr = hourly_data.get(key, [])
                val = arr[i] if i < len(arr) else None
                return val

            record = WeatherHourly(
                location_id=location_id,
                forecast_time=forecast_time,
                temperature_2m=safe_get("temperature_2m"),
                apparent_temp=safe_get("apparent_temperature"),
                relative_humidity=safe_get("relative_humidity_2m"),
                dew_point=safe_get("dew_point_2m"),
                precipitation_prob=safe_get("precipitation_probability"),
                precipitation_mm=safe_get("precipitation"),
                rain_mm=safe_get("rain"),
                wind_speed_10m=safe_get("wind_speed_10m"),
                wind_gusts_10m=safe_get("wind_gusts_10m"),
                wind_direction=safe_get("wind_direction_10m"),
                uv_index=safe_get("uv_index"),
                cloud_cover=safe_get("cloud_cover"),
                visibility=safe_get("visibility"),
                weather_code=safe_get("weathercode"),
                surface_pressure=safe_get("surface_pressure"),
            )

            # UPSERT: Update if (location_id, forecast_time) exists
            existing = (
                db.query(WeatherHourly)
                .filter_by(location_id=location_id, forecast_time=forecast_time)
                .first()
            )

            if existing:
                # Update existing record
                for field in [
                    "temperature_2m", "apparent_temp", "relative_humidity",
                    "dew_point", "precipitation_prob", "precipitation_mm",
                    "rain_mm", "wind_speed_10m", "wind_gusts_10m",
                    "wind_direction", "uv_index", "cloud_cover",
                    "visibility", "weather_code", "surface_pressure"
                ]:
                    setattr(existing, field, getattr(record, field))
            else:
                db.add(record)

            inserted += 1

        except Exception as e:
            logger.warning(f"⚠️  Skipping hourly record at index {i}: {e}")
            continue

    db.commit()
    logger.success(f"✅ Hourly data: {inserted} records upserted for location_id={location_id}")
    return inserted


# ──────────────────────────────────────────────────────────
# PARSE & STORE DAILY DATA
# ──────────────────────────────────────────────────────────

def parse_and_store_daily(
    db: Session,
    location_id: int,
    daily_data: dict,
) -> int:
    """
    Parses the 'daily' section of Open-Meteo API response and
    upserts records into weather_daily table.

    Parameters:
        db          : SQLAlchemy session
        location_id : FK to locations table
        daily_data  : The 'daily' dict from API response

    Returns:
        Number of records upserted
    """
    dates = daily_data.get("time", [])
    if not dates:
        logger.warning("⚠️  No daily date entries found in API response.")
        return 0

    inserted = 0

    for i, date_str in enumerate(dates):
        try:
            forecast_date = datetime.strptime(date_str, "%Y-%m-%d")

            def safe_get(key: str):
                arr = daily_data.get(key, [])
                return arr[i] if i < len(arr) else None

            record = WeatherDaily(
                location_id=location_id,
                forecast_date=forecast_date,
                temp_max=safe_get("temperature_2m_max"),
                temp_min=safe_get("temperature_2m_min"),
                apparent_temp_max=safe_get("apparent_temperature_max"),
                apparent_temp_min=safe_get("apparent_temperature_min"),
                precipitation_sum=safe_get("precipitation_sum"),
                precipitation_prob_max=safe_get("precipitation_probability_max"),
                wind_speed_max=safe_get("wind_speed_10m_max"),
                wind_gusts_max=safe_get("wind_gusts_10m_max"),
                uv_index_max=safe_get("uv_index_max"),
                sunrise=safe_get("sunrise"),
                sunset=safe_get("sunset"),
                weather_code=safe_get("weathercode"),
            )

            # UPSERT
            existing = (
                db.query(WeatherDaily)
                .filter_by(location_id=location_id, forecast_date=forecast_date)
                .first()
            )

            if existing:
                for field in [
                    "temp_max", "temp_min", "apparent_temp_max", "apparent_temp_min",
                    "precipitation_sum", "precipitation_prob_max",
                    "wind_speed_max", "wind_gusts_max", "uv_index_max",
                    "sunrise", "sunset", "weather_code"
                ]:
                    setattr(existing, field, getattr(record, field))
            else:
                db.add(record)

            inserted += 1

        except Exception as e:
            logger.warning(f"⚠️  Skipping daily record at index {i}: {e}")
            continue

    db.commit()
    logger.success(f"✅ Daily data: {inserted} records upserted for location_id={location_id}")
    return inserted


# ──────────────────────────────────────────────────────────
# MAIN INGESTION FUNCTION
# ──────────────────────────────────────────────────────────

def fetch_weather_for_location(
    location: Location,
    db: Session,
) -> dict:
    """
    Full ingestion pipeline for a single location:
      1. Call Open-Meteo API
      2. Save raw JSON
      3. Parse + store hourly data
      4. Parse + store daily data

    Parameters:
        location : Location ORM object
        db       : SQLAlchemy session

    Returns:
        Summary dict with counts and status
    """
    logger.info(f"🌦️  Starting ingestion for: {location.city} ({location.latitude}, {location.longitude})")

    result = {
        "location": location.city,
        "status": "error",
        "hourly_records": 0,
        "daily_records": 0,
        "error": None,
    }

    try:
        # Step 1: Fetch from API
        raw_data = call_open_meteo_api(
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
        )

        # Step 2: Store raw response
        save_raw_response(db, location.id, raw_data)

        # Step 3: Parse and store hourly
        hourly_count = parse_and_store_hourly(
            db, location.id, raw_data.get("hourly", {})
        )

        # Step 4: Parse and store daily
        daily_count = parse_and_store_daily(
            db, location.id, raw_data.get("daily", {})
        )

        result.update({
            "status": "success",
            "hourly_records": hourly_count,
            "daily_records": daily_count,
        })

    except httpx.HTTPStatusError as e:
        error_msg = f"API HTTP error: {e.response.status_code} — {e.response.text[:200]}"
        logger.error(f"❌ {error_msg}")
        save_raw_response(db, location.id, {}, status="error", error_msg=error_msg)
        result["error"] = error_msg

    except httpx.TimeoutException:
        error_msg = "API request timed out (30s)"
        logger.error(f"❌ {error_msg}")
        save_raw_response(db, location.id, {}, status="error", error_msg=error_msg)
        result["error"] = error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        save_raw_response(db, location.id, {}, status="error", error_msg=error_msg)
        result["error"] = error_msg

    return result


def fetch_all_locations(db: Session) -> list[dict]:
    """
    Runs the ingestion pipeline for ALL active locations.
    Called by the APScheduler job every N hours.

    Returns:
        List of result dicts, one per location
    """
    locations = db.query(Location).filter(Location.is_active == True).all()

    if not locations:
        logger.warning("⚠️  No active locations found. Add locations first.")
        return []

    logger.info(f"🔄 Refreshing weather for {len(locations)} locations...")
    results = []

    for loc in locations:
        result = fetch_weather_for_location(loc, db)
        results.append(result)

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.success(f"✅ Ingestion complete: {success_count}/{len(locations)} locations updated.")
    return results


# ──────────────────────────────────────────────────────────
# Script entry point — run ingestion manually
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from db.database import SessionLocal, init_db

    logger.info("🚀 Manual ingestion run started...")
    init_db()

    db = SessionLocal()
    try:
        results = fetch_all_locations(db)
        for r in results:
            status_icon = "✅" if r["status"] == "success" else "❌"
            print(f"{status_icon} {r['location']}: {r['hourly_records']} hourly, {r['daily_records']} daily")
    finally:
        db.close()
