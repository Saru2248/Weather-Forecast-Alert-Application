"""
============================================================
api/schemas.py — Pydantic Response Schemas (DTOs)
============================================================
Defines the data shapes for all API responses.
These ensure consistent, documented API contracts.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────
# Location Schemas
# ──────────────────────────────────────────────────────────

class LocationBase(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────
# Hourly Weather Schemas
# ──────────────────────────────────────────────────────────

class HourlyWeatherResponse(BaseModel):
    id: int
    location_id: int
    forecast_time: datetime
    temperature_2m: Optional[float] = None
    apparent_temp: Optional[float] = None
    relative_humidity: Optional[float] = None
    precipitation_prob: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    wind_gusts_10m: Optional[float] = None
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────
# Daily Weather Schemas
# ──────────────────────────────────────────────────────────

class DailyWeatherResponse(BaseModel):
    id: int
    location_id: int
    forecast_date: datetime
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    apparent_temp_max: Optional[float] = None
    apparent_temp_min: Optional[float] = None
    precipitation_sum: Optional[float] = None
    precipitation_prob_max: Optional[float] = None
    wind_speed_max: Optional[float] = None
    wind_gusts_max: Optional[float] = None
    uv_index_max: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    weather_code: Optional[int] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────
# Alert Schemas
# ──────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    location_id: int
    alert_type: str
    severity: str
    title: str
    message: str
    trigger_value: Optional[float] = None
    threshold_used: Optional[float] = None
    forecast_time: Optional[datetime] = None
    alert_time: datetime
    is_notified: bool
    is_active: bool

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────
# Generic Response Schemas
# ──────────────────────────────────────────────────────────

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class IngestionResponse(BaseModel):
    location: str
    status: str
    hourly_records: int
    daily_records: int
    error: Optional[str] = None


class AlertSummary(BaseModel):
    total_alerts: int
    critical: int
    high: int
    medium: int
    low: int
    by_type: dict


class CurrentWeatherResponse(BaseModel):
    city: str
    latitude: float
    longitude: float
    timezone: str
    temperature: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_gusts: Optional[float] = None
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None
    precipitation_prob: Optional[float] = None
    weather_description: str = "N/A"
    last_updated: Optional[datetime] = None
