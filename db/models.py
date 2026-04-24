"""
============================================================
db/models.py — SQLAlchemy ORM Table Definitions
============================================================
Defines ALL database tables for the Weather App:

  - locations       : cities tracked by the system
  - weather_raw     : raw JSON responses from API
  - weather_hourly  : parsed hourly forecast data
  - weather_daily   : parsed daily summary data
  - alerts_log      : generated weather alerts

Relationships:
  Location (1) ──── (M) WeatherRaw
  Location (1) ──── (M) WeatherHourly
  Location (1) ──── (M) WeatherDaily
  Location (1) ──── (M) AlertLog
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    DateTime, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ──────────────────────────────────────────────────────────
# TABLE: locations
# ──────────────────────────────────────────────────────────
class Location(Base):
    """
    Represents a geographic location tracked by the system.
    Stores city name, country, and precise lat/lon coordinates.
    """
    __tablename__ = "locations"

    id         = Column(Integer, primary_key=True, index=True)
    city       = Column(String(100), nullable=False)
    country    = Column(String(100), nullable=False, default="India")
    latitude   = Column(Float, nullable=False)
    longitude  = Column(Float, nullable=False)
    timezone   = Column(String(50), nullable=False, default="Asia/Kolkata")
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Ensure no duplicate city entries
    __table_args__ = (
        UniqueConstraint("city", "latitude", "longitude", name="uq_location"),
    )

    # Relationships
    raw_data    = relationship("WeatherRaw",    back_populates="location", cascade="all, delete")
    hourly_data = relationship("WeatherHourly", back_populates="location", cascade="all, delete")
    daily_data  = relationship("WeatherDaily",  back_populates="location", cascade="all, delete")
    alerts      = relationship("AlertLog",      back_populates="location", cascade="all, delete")

    def __repr__(self):
        return f"<Location(city={self.city}, lat={self.latitude}, lon={self.longitude})>"


# ──────────────────────────────────────────────────────────
# TABLE: weather_raw
# ──────────────────────────────────────────────────────────
class WeatherRaw(Base):
    """
    Stores the raw JSON response from the Open-Meteo API.
    This is the source-of-truth audit trail — nothing is discarded.
    Raw data can be reprocessed if parsing logic changes.
    """
    __tablename__ = "weather_raw"

    id          = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    fetched_at  = Column(DateTime, default=datetime.utcnow, index=True)
    api_source  = Column(String(50), default="open-meteo")
    raw_json    = Column(Text, nullable=False)   # full JSON as string
    status      = Column(String(20), default="success")  # success / error
    error_msg   = Column(Text, nullable=True)

    location = relationship("Location", back_populates="raw_data")

    __table_args__ = (
        Index("ix_weather_raw_location_fetched", "location_id", "fetched_at"),
    )

    def __repr__(self):
        return f"<WeatherRaw(location_id={self.location_id}, fetched_at={self.fetched_at})>"


# ──────────────────────────────────────────────────────────
# TABLE: weather_hourly
# ──────────────────────────────────────────────────────────
class WeatherHourly(Base):
    """
    Stores parsed hourly weather forecast for each location.
    One row = one hour of forecast data.

    Key variables:
      - temperature_2m      : Air temp at 2m height (°C)
      - relative_humidity   : % humidity
      - precipitation_prob  : Probability of rain (%)
      - wind_speed          : km/h
      - wind_gusts          : Maximum wind gust (km/h)
      - uv_index            : UV radiation index (0–11+)
      - cloud_cover         : % sky covered by clouds
      - weather_code        : WMO weather code
    """
    __tablename__ = "weather_hourly"

    id                  = Column(Integer, primary_key=True, index=True)
    location_id         = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    forecast_time       = Column(DateTime, nullable=False, index=True)
    temperature_2m      = Column(Float, nullable=True)
    apparent_temp       = Column(Float, nullable=True)   # "feels like"
    relative_humidity   = Column(Float, nullable=True)
    dew_point           = Column(Float, nullable=True)
    precipitation_prob  = Column(Float, nullable=True)
    precipitation_mm    = Column(Float, nullable=True)
    rain_mm             = Column(Float, nullable=True)
    wind_speed_10m      = Column(Float, nullable=True)
    wind_gusts_10m      = Column(Float, nullable=True)
    wind_direction      = Column(Float, nullable=True)
    uv_index            = Column(Float, nullable=True)
    cloud_cover         = Column(Float, nullable=True)
    visibility          = Column(Float, nullable=True)
    weather_code        = Column(Integer, nullable=True)
    surface_pressure    = Column(Float, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location", back_populates="hourly_data")

    __table_args__ = (
        UniqueConstraint("location_id", "forecast_time", name="uq_hourly_forecast"),
        Index("ix_hourly_location_time", "location_id", "forecast_time"),
    )

    def __repr__(self):
        return f"<WeatherHourly(location_id={self.location_id}, time={self.forecast_time}, temp={self.temperature_2m})>"


# ──────────────────────────────────────────────────────────
# TABLE: weather_daily
# ──────────────────────────────────────────────────────────
class WeatherDaily(Base):
    """
    Stores daily weather summary for each location.
    One row = one day of forecast summary.
    """
    __tablename__ = "weather_daily"

    id                    = Column(Integer, primary_key=True, index=True)
    location_id           = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    forecast_date         = Column(DateTime, nullable=False, index=True)
    temp_max              = Column(Float, nullable=True)
    temp_min              = Column(Float, nullable=True)
    apparent_temp_max     = Column(Float, nullable=True)
    apparent_temp_min     = Column(Float, nullable=True)
    precipitation_sum     = Column(Float, nullable=True)
    precipitation_prob_max= Column(Float, nullable=True)
    wind_speed_max        = Column(Float, nullable=True)
    wind_gusts_max        = Column(Float, nullable=True)
    uv_index_max          = Column(Float, nullable=True)
    sunrise               = Column(String(30), nullable=True)
    sunset                = Column(String(30), nullable=True)
    weather_code          = Column(Integer, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location", back_populates="daily_data")

    __table_args__ = (
        UniqueConstraint("location_id", "forecast_date", name="uq_daily_forecast"),
        Index("ix_daily_location_date", "location_id", "forecast_date"),
    )

    def __repr__(self):
        return f"<WeatherDaily(location_id={self.location_id}, date={self.forecast_date}, max={self.temp_max})>"


# ──────────────────────────────────────────────────────────
# TABLE: alerts_log
# ──────────────────────────────────────────────────────────
class AlertLog(Base):
    """
    Stores every weather alert generated by the Alert Engine.
    Used for:
      - Deduplication (don't re-alert same condition)
      - Historical reporting
      - Dashboard display

    Alert types: RAIN | HEAT | WIND | UV
    Severity:    LOW  | MEDIUM | HIGH | CRITICAL
    """
    __tablename__ = "alerts_log"

    id             = Column(Integer, primary_key=True, index=True)
    location_id    = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    alert_type     = Column(String(20), nullable=False)    # RAIN / HEAT / WIND / UV
    severity       = Column(String(20), nullable=False)    # LOW / MEDIUM / HIGH / CRITICAL
    title          = Column(String(200), nullable=False)
    message        = Column(Text, nullable=False)
    trigger_value  = Column(Float, nullable=True)          # value that triggered alert
    threshold_used = Column(Float, nullable=True)          # configured threshold
    forecast_time  = Column(DateTime, nullable=True)       # when the condition is expected
    alert_time     = Column(DateTime, default=datetime.utcnow, index=True)
    is_notified    = Column(Boolean, default=False)        # was notification sent?
    notified_at    = Column(DateTime, nullable=True)
    is_active      = Column(Boolean, default=True)         # still relevant?

    location = relationship("Location", back_populates="alerts")

    __table_args__ = (
        Index("ix_alert_location_type_time", "location_id", "alert_type", "alert_time"),
    )

    def __repr__(self):
        return f"<AlertLog(type={self.alert_type}, severity={self.severity}, location_id={self.location_id})>"
