"""
============================================================
src/rules.py — Alert Engine / Rule Processing Module
============================================================
The Alert Engine evaluates stored weather forecast data
against configurable thresholds and generates structured
alert objects.

Alert Types:
  - RAIN  : Probability of rain > threshold (default: 60%)
  - HEAT  : Temperature ≥ threshold (default: 40°C)
  - WIND  : Wind gust ≥ threshold (default: 60 km/h)
  - UV    : UV index ≥ threshold (default: 8)

Severity Levels:
  - LOW      : Condition exceeded slightly
  - MEDIUM   : Noticeable impact expected
  - HIGH     : Significant impact, take precautions
  - CRITICAL : Extreme condition, immediate action

Alert Deduplication:
  - Same alert_type + location within the SAME DAY is skipped
  - Prevents flooding the alerts table with repeated entries

Usage:
    alerts = run_alert_engine(location_id=1, db=db)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.models import Location, WeatherHourly, WeatherDaily, AlertLog


# ──────────────────────────────────────────────────────────
# SEVERITY HELPERS
# ──────────────────────────────────────────────────────────

def get_rain_severity(probability: float) -> str:
    """Maps rain probability % to severity level."""
    if probability >= 90:
        return "CRITICAL"
    elif probability >= 80:
        return "HIGH"
    elif probability >= 70:
        return "MEDIUM"
    else:
        return "LOW"


def get_heat_severity(temperature: float) -> str:
    """Maps temperature °C to severity level."""
    if temperature >= 48:
        return "CRITICAL"
    elif temperature >= 45:
        return "HIGH"
    elif temperature >= 42:
        return "MEDIUM"
    else:
        return "LOW"


def get_wind_severity(gust_speed: float) -> str:
    """Maps wind gust km/h to severity level."""
    if gust_speed >= 120:
        return "CRITICAL"
    elif gust_speed >= 90:
        return "HIGH"
    elif gust_speed >= 75:
        return "MEDIUM"
    else:
        return "LOW"


def get_uv_severity(uv_index: float) -> str:
    """Maps UV index to severity level per WHO guidelines."""
    if uv_index >= 11:
        return "CRITICAL"  # Extreme
    elif uv_index >= 10:
        return "HIGH"      # Very High
    elif uv_index >= 8:
        return "MEDIUM"    # High
    else:
        return "LOW"


# ──────────────────────────────────────────────────────────
# WMO WEATHER CODE INTERPRETER
# ──────────────────────────────────────────────────────────

WMO_CODES = {
    0:  "Clear sky",
    1:  "Mainly clear",
    2:  "Partly cloudy",
    3:  "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def interpret_weather_code(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODES.get(code, f"Code {code}")


# ──────────────────────────────────────────────────────────
# DEDUPLICATION CHECK
# ──────────────────────────────────────────────────────────

def is_duplicate_alert(
    db: Session,
    location_id: int,
    alert_type: str,
    hours_window: int = 12,
) -> bool:
    """
    Returns True if an alert of the same type was already
    generated for this location within the last N hours.

    This prevents the same RAIN alert from being created
    dozens of times during a 3-hour refresh cycle.

    Parameters:
        db           : SQLAlchemy session
        location_id  : Location to check
        alert_type   : RAIN / HEAT / WIND / UV
        hours_window : Deduplication window in hours
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_window)

    existing = (
        db.query(AlertLog)
        .filter(
            AlertLog.location_id == location_id,
            AlertLog.alert_type == alert_type,
            AlertLog.alert_time >= cutoff_time,
            AlertLog.is_active == True,
        )
        .first()
    )

    return existing is not None


# ──────────────────────────────────────────────────────────
# INDIVIDUAL ALERT RULE EVALUATORS
# ──────────────────────────────────────────────────────────

def evaluate_rain_alert(
    db: Session,
    location: Location,
    hourly_records: list[WeatherHourly],
) -> Optional[AlertLog]:
    """
    Rule: If precipitation_probability > RAIN_PROBABILITY_THRESHOLD
    for any upcoming hourly record, generate a RAIN alert.

    Returns the AlertLog ORM object (not yet committed to DB),
    or None if no alert is warranted.
    """
    threshold = settings.RAIN_PROBABILITY_THRESHOLD

    # Find the worst upcoming rain period
    worst_record = None
    worst_prob = 0.0

    for record in hourly_records:
        prob = record.precipitation_prob or 0.0
        if prob > worst_prob:
            worst_prob = prob
            worst_record = record

    if worst_prob < threshold:
        return None

    if is_duplicate_alert(db, location.id, "RAIN"):
        logger.debug(f"🔕 Duplicate RAIN alert skipped for {location.city}")
        return None

    severity = get_rain_severity(worst_prob)
    forecast_time_str = worst_record.forecast_time.strftime("%d %b %Y %H:%M") if worst_record else "N/A"

    alert = AlertLog(
        location_id=location.id,
        alert_type="RAIN",
        severity=severity,
        title=f"🌧️ Rain Alert — {location.city}",
        message=(
            f"High probability of rainfall detected in {location.city}.\n"
            f"Peak rain probability: {worst_prob:.0f}% at {forecast_time_str}.\n"
            f"Expected precipitation: {worst_record.precipitation_mm or 0:.1f} mm.\n"
            f"Severity: {severity}. Carry an umbrella and avoid low-lying areas."
        ),
        trigger_value=worst_prob,
        threshold_used=threshold,
        forecast_time=worst_record.forecast_time if worst_record else None,
    )

    logger.warning(f"🌧️  [{severity}] RAIN alert generated for {location.city} ({worst_prob:.0f}%)")
    return alert


def evaluate_heat_alert(
    db: Session,
    location: Location,
    hourly_records: list[WeatherHourly],
) -> Optional[AlertLog]:
    """
    Rule: If temperature_2m ≥ HEAT_TEMPERATURE_THRESHOLD
    for any upcoming record, generate a HEAT alert.
    """
    threshold = settings.HEAT_TEMPERATURE_THRESHOLD

    worst_record = None
    worst_temp = -999.0

    for record in hourly_records:
        temp = record.temperature_2m
        if temp is not None and temp > worst_temp:
            worst_temp = temp
            worst_record = record

    if worst_temp < threshold:
        return None

    if is_duplicate_alert(db, location.id, "HEAT"):
        logger.debug(f"🔕 Duplicate HEAT alert skipped for {location.city}")
        return None

    severity = get_heat_severity(worst_temp)
    feels_like = worst_record.apparent_temp if worst_record else None
    forecast_time_str = worst_record.forecast_time.strftime("%d %b %Y %H:%M") if worst_record else "N/A"

    alert = AlertLog(
        location_id=location.id,
        alert_type="HEAT",
        severity=severity,
        title=f"🌡️ Heat Alert — {location.city}",
        message=(
            f"Extreme heat conditions expected in {location.city}.\n"
            f"Peak temperature: {worst_temp:.1f}°C at {forecast_time_str}.\n"
            f"Feels like: {feels_like:.1f}°C.\n" if feels_like else ""
            f"Severity: {severity}. Stay hydrated, avoid outdoor activity 11AM–4PM."
        ),
        trigger_value=worst_temp,
        threshold_used=threshold,
        forecast_time=worst_record.forecast_time if worst_record else None,
    )

    logger.warning(f"🌡️  [{severity}] HEAT alert generated for {location.city} ({worst_temp:.1f}°C)")
    return alert


def evaluate_wind_alert(
    db: Session,
    location: Location,
    hourly_records: list[WeatherHourly],
) -> Optional[AlertLog]:
    """
    Rule: If wind_gusts_10m ≥ WIND_GUST_THRESHOLD
    for any upcoming record, generate a WIND alert.
    """
    threshold = settings.WIND_GUST_THRESHOLD

    worst_record = None
    worst_gust = 0.0

    for record in hourly_records:
        gust = record.wind_gusts_10m or 0.0
        if gust > worst_gust:
            worst_gust = gust
            worst_record = record

    if worst_gust < threshold:
        return None

    if is_duplicate_alert(db, location.id, "WIND"):
        logger.debug(f"🔕 Duplicate WIND alert skipped for {location.city}")
        return None

    severity = get_wind_severity(worst_gust)
    forecast_time_str = worst_record.forecast_time.strftime("%d %b %Y %H:%M") if worst_record else "N/A"
    wind_speed = worst_record.wind_speed_10m or 0.0

    alert = AlertLog(
        location_id=location.id,
        alert_type="WIND",
        severity=severity,
        title=f"💨 Wind Alert — {location.city}",
        message=(
            f"Strong wind conditions forecast for {location.city}.\n"
            f"Peak wind gust: {worst_gust:.0f} km/h at {forecast_time_str}.\n"
            f"Sustained wind speed: {wind_speed:.0f} km/h.\n"
            f"Severity: {severity}. Secure loose objects, avoid coastal areas."
        ),
        trigger_value=worst_gust,
        threshold_used=threshold,
        forecast_time=worst_record.forecast_time if worst_record else None,
    )

    logger.warning(f"💨  [{severity}] WIND alert generated for {location.city} ({worst_gust:.0f} km/h)")
    return alert


def evaluate_uv_alert(
    db: Session,
    location: Location,
    hourly_records: list[WeatherHourly],
) -> Optional[AlertLog]:
    """
    Rule: If uv_index ≥ UV_INDEX_THRESHOLD (default 8 = High)
    for any upcoming daytime record, generate a UV alert.

    WHO UV Index Scale:
      0–2   : Low
      3–5   : Moderate
      6–7   : High
      8–10  : Very High
      11+   : Extreme
    """
    threshold = settings.UV_INDEX_THRESHOLD

    worst_record = None
    worst_uv = 0.0

    for record in hourly_records:
        uv = record.uv_index or 0.0
        if uv > worst_uv:
            worst_uv = uv
            worst_record = record

    if worst_uv < threshold:
        return None

    if is_duplicate_alert(db, location.id, "UV"):
        logger.debug(f"🔕 Duplicate UV alert skipped for {location.city}")
        return None

    severity = get_uv_severity(worst_uv)
    forecast_time_str = worst_record.forecast_time.strftime("%d %b %Y %H:%M") if worst_record else "N/A"

    who_label = (
        "Extreme" if worst_uv >= 11
        else "Very High" if worst_uv >= 8
        else "High"
    )

    alert = AlertLog(
        location_id=location.id,
        alert_type="UV",
        severity=severity,
        title=f"☀️ UV Alert — {location.city}",
        message=(
            f"Dangerously high UV radiation expected in {location.city}.\n"
            f"Peak UV Index: {worst_uv:.1f} ({who_label}) at {forecast_time_str}.\n"
            f"Severity: {severity}. Apply SPF 50+ sunscreen, wear protective clothing."
        ),
        trigger_value=worst_uv,
        threshold_used=threshold,
        forecast_time=worst_record.forecast_time if worst_record else None,
    )

    logger.warning(f"☀️  [{severity}] UV alert generated for {location.city} (UV={worst_uv:.1f})")
    return alert


# ──────────────────────────────────────────────────────────
# MAIN ALERT ENGINE
# ──────────────────────────────────────────────────────────

def run_alert_engine(location_id: int, db: Session) -> list[AlertLog]:
    """
    Runs all alert rules for a given location and persists
    new alerts to the alerts_log table.

    Parameters:
        location_id : ID of the location to evaluate
        db          : SQLAlchemy session

    Returns:
        List of AlertLog objects that were newly created
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        logger.error(f"❌ Location ID {location_id} not found.")
        return []

    logger.info(f"🔍 Running alert engine for: {location.city}")

    # Fetch next 24 hours of hourly forecasts (upcoming only)
    now = datetime.utcnow()
    look_ahead = now + timedelta(hours=24)

    hourly_records = (
        db.query(WeatherHourly)
        .filter(
            WeatherHourly.location_id == location_id,
            WeatherHourly.forecast_time >= now,
            WeatherHourly.forecast_time <= look_ahead,
        )
        .order_by(WeatherHourly.forecast_time)
        .all()
    )

    if not hourly_records:
        logger.warning(f"⚠️  No upcoming hourly data for {location.city}. Run ingestion first.")
        return []

    logger.debug(f"📊 Evaluating {len(hourly_records)} hourly records for {location.city}")

    # Evaluate all rules
    new_alerts = []
    rule_evaluators = [
        evaluate_rain_alert,
        evaluate_heat_alert,
        evaluate_wind_alert,
        evaluate_uv_alert,
    ]

    for evaluator in rule_evaluators:
        alert = evaluator(db, location, hourly_records)
        if alert:
            db.add(alert)
            new_alerts.append(alert)

    db.commit()

    # Refresh to get IDs
    for alert in new_alerts:
        db.refresh(alert)

    if new_alerts:
        logger.success(f"🚨 {len(new_alerts)} new alert(s) generated for {location.city}")
    else:
        logger.info(f"✅ No alerts triggered for {location.city} — all conditions normal.")

    return new_alerts


def run_alert_engine_all_locations(db: Session) -> dict:
    """
    Runs the alert engine for all active locations.
    Called by the scheduler after each data ingestion.

    Returns:
        Summary dict: {location_name: alert_count}
    """
    locations = db.query(Location).filter(Location.is_active == True).all()
    summary = {}

    for loc in locations:
        alerts = run_alert_engine(loc.id, db)
        summary[loc.city] = len(alerts)

    total = sum(summary.values())
    logger.success(f"✅ Alert engine complete. Total new alerts: {total}")
    return summary


# ──────────────────────────────────────────────────────────
# Script entry point — run alert engine manually
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from db.database import SessionLocal, init_db

    logger.info("🚀 Manual alert engine run started...")
    init_db()

    db = SessionLocal()
    try:
        summary = run_alert_engine_all_locations(db)
        print("\n📋 Alert Summary:")
        for city, count in summary.items():
            icon = "🚨" if count > 0 else "✅"
            print(f"  {icon} {city}: {count} alert(s)")
    finally:
        db.close()
