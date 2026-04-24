# 🌦️ Weather Forecast & Alert Application

> **Industry-grade Weather Intelligence System** — Real-time forecasts, intelligent alerts, and a beautiful dashboard powered by Open-Meteo API, FastAPI, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?style=flat-square&logo=streamlit)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey?style=flat-square&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Alert Rules](#alert-rules)
- [Screenshots](#screenshots)
- [Deployment](#deployment)
- [Interview Prep](#interview-prep)

---

## 🎯 Overview

This system simulates a **production-grade weather intelligence platform** used in industries like:

| Industry | Use Case |
|----------|----------|
| 🚚 Logistics | Route planning around storms, wind alerts |
| 🌾 Agriculture | Frost/rain alerts for crop protection |
| ✈️ Travel | Flight delay prediction, UV warnings |
| ⚡ Energy | Solar/wind energy forecasting |
| 🚨 Public Safety | Heat waves, cyclone early warning |

The system fetches **real weather data** (no simulation) from the free [Open-Meteo API](https://open-meteo.com), processes it through a rule-based alert engine, and displays everything in a live dashboard.

---

## ✨ Features

- ✅ **Real Weather Data** — Open-Meteo API (free, no API key needed)
- ✅ **5-Table Relational DB** — SQLite with SQLAlchemy ORM
- ✅ **4 Alert Types** — Rain, Heat, Wind, UV with severity levels
- ✅ **FastAPI Backend** — 12+ REST endpoints with Swagger docs
- ✅ **Streamlit Dashboard** — Dark UI, interactive Plotly charts
- ✅ **Auto-Refresh Scheduler** — APScheduler (every 3 hours)
- ✅ **Notification System** — Email (SMTP) + Telegram bot support
- ✅ **Alert Deduplication** — No repeated alerts for same condition
- ✅ **10 Indian Cities** pre-seeded (Mumbai, Delhi, Bangalore, etc.)
- ✅ **Docker Support** — Containerized deployment ready

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FLOW                                 │
│                                                             │
│  Open-Meteo API                                             │
│       │                                                     │
│       ▼                                                     │
│  [Ingestion Module] ──► [weather_raw table]                 │
│       │                                                     │
│       ▼                                                     │
│  [Parser] ──► [weather_hourly] + [weather_daily]           │
│       │                                                     │
│       ▼                                                     │
│  [Alert Engine] ──► [alerts_log table]                      │
│       │                                                     │
│       ▼                                                     │
│  [Notification] ──► Email / Telegram                        │
│                                                             │
│  [FastAPI Layer] ←──── All tables                           │
│       │                                                     │
│       ▼                                                     │
│  [Streamlit Dashboard] ◄── REST API calls                   │
│                                                             │
│  [APScheduler] ──► Runs entire pipeline every 3h            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Source | Open-Meteo API | Free weather data (no key) |
| Backend | FastAPI + Uvicorn | REST API server |
| Database | SQLite + SQLAlchemy | Data storage & ORM |
| Processing | Python + Pandas | Data transformation |
| Alert Engine | Custom rule engine | Threshold evaluation |
| Scheduler | APScheduler | Auto-refresh every 3h |
| Dashboard | Streamlit + Plotly | Interactive UI |
| Notifications | SMTP + Telegram | Alert delivery |
| Deployment | Docker + Docker Compose | Containerization |

---

## 📁 Project Structure

```
weather-app/
├── api/
│   ├── app.py          # FastAPI routes (12+ endpoints)
│   └── schemas.py      # Pydantic response models
├── src/
│   ├── ingestion.py    # Weather API fetch + parse + store
│   └── rules.py        # Alert engine (RAIN/HEAT/WIND/UV)
├── db/
│   ├── models.py       # SQLAlchemy ORM (5 tables)
│   └── database.py     # Engine + sessions + seeding
├── jobs/
│   └── refresh.py      # APScheduler background job
├── notify/
│   └── alert.py        # Email + Telegram notifications
├── frontend/
│   └── dashboard.py    # Streamlit dashboard
├── main.py             # Unified entry point
├── config.py           # Centralized settings
├── .env                # Environment variables
├── requirements.txt    # Dependencies
├── run.bat             # Windows quick-start script
├── Dockerfile          # Container definition
└── docker-compose.yml  # Multi-service orchestration
```

---

## 🚀 Quick Start

### Option 1: One-Click (Windows)
```bash
Double-click run.bat
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Terminal 1) Start FastAPI backend
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# 3. (Terminal 2) Start Streamlit dashboard
streamlit run frontend/dashboard.py

# 4. (Optional Terminal 3) Start background scheduler
python jobs/refresh.py
```

### Access Points
| Service | URL |
|---------|-----|
| 🖥️ Dashboard | http://localhost:8501 |
| 🔌 API | http://localhost:8000 |
| 📚 Swagger Docs | http://localhost:8000/docs |
| 📖 ReDoc | http://localhost:8000/redoc |

### First Run Steps
1. Open dashboard → click **🔄 Refresh Data** (fetches live weather)
2. Click **🚨 Run Alerts** (generates alerts from fetched data)
3. View charts and alerts in the dashboard tabs

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/locations` | List all cities |
| POST | `/api/locations` | Add new city |
| GET | `/api/weather/current/{id}` | Current conditions |
| GET | `/api/forecast/hourly/{id}?hours=24` | Hourly forecast |
| GET | `/api/forecast/daily/{id}?days=7` | Daily forecast |
| GET | `/api/alerts` | All recent alerts |
| GET | `/api/alerts/{location_id}` | City-specific alerts |
| POST | `/api/ingest/{location_id}` | Manual data refresh |
| POST | `/api/ingest/all` | Refresh all cities |
| POST | `/api/alerts/run/{id}` | Run alert engine |
| GET | `/api/summary` | Dashboard statistics |

---

## 🚨 Alert Rules

| Alert | Condition | Threshold | Severity Scale |
|-------|-----------|-----------|----------------|
| 🌧️ RAIN | Rain probability | > 60% | LOW→MED→HIGH→CRITICAL |
| 🌡️ HEAT | Temperature | ≥ 40°C | LOW→MED→HIGH→CRITICAL |
| 💨 WIND | Wind gusts | ≥ 60 km/h | LOW→MED→HIGH→CRITICAL |
| ☀️ UV | UV Index | ≥ 8 (WHO High) | LOW→MED→HIGH→CRITICAL |

All thresholds are configurable via `.env`.

---

## 🐳 Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f api
```

---

## ☁️ Cloud Deployment (Render)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect GitHub repo
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `uvicorn api.app:app --host 0.0.0.0 --port $PORT`
6. Deploy! (Free tier available)

---

## 📅 Build Timeline

| Day | Task |
|-----|------|
| Day 1 | Setup project structure, install dependencies, configure .env |
| Day 2 | Build ingestion module, test Open-Meteo API, store raw data |
| Day 3 | Create DB models, write alert engine rules |
| Day 4 | Build FastAPI endpoints, test with Swagger UI |
| Day 5 | Build Streamlit dashboard, add charts and alert cards |
| Day 6 | Add scheduler, notification system, Docker setup |
| Day 7 | Test end-to-end, write README, push to GitHub |

---

## 🎤 Interview Prep

**Q: Why did you choose Open-Meteo over OpenWeatherMap?**  
A: Open-Meteo is fully free with no API key required, offers up to 16-day forecasts, and provides granular hourly data with UV index and wind gusts — ideal for demonstrating a production-grade alert engine.

**Q: How does the deduplication logic work?**  
A: The alert engine checks `alerts_log` for any alert of the same type for the same location within the last 12 hours before inserting a new one. This prevents alert floods during frequent refreshes.

**Q: How would you scale this for thousands of cities?**  
A: Replace SQLite with PostgreSQL, use Celery with Redis for distributed task queuing, add Redis caching for API responses, and containerize with Kubernetes for horizontal scaling.

**Q: What's the data flow end-to-end?**  
A: Open-Meteo API → `ingestion.py` fetches + parses → stored in `weather_raw` (audit) + `weather_hourly/daily` (structured) → `rules.py` evaluates thresholds → `alerts_log` persisted → `notify/alert.py` sends email/Telegram → Streamlit reads via FastAPI REST calls.

---

## 🔮 Future Improvements

- 🗺️ Leaflet.js map with city pins and alert overlays
- 🌫️ AQI (Air Quality Index) integration
- 🤖 ML-based weather prediction (LSTM/Prophet)
- 📱 Mobile push notifications (Firebase)
- 📊 Historical trend analysis dashboard
- 🔔 WhatsApp alerts via Twilio

---


---

<div align="center">
  Built with ❤️ for placement projects and GitHub portfolios<br/>
  <strong>Star ⭐ this repo if it helped you!</strong>
</div>
#   W e a t h e r - F o r e c a s t - A l e r t - A p p l i c a t i o n  
 