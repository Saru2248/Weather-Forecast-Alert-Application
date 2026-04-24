Here’s a **clean, professional, interview-ready README.md** — rewritten to sound like a real engineer built it (not a student template), with stronger positioning, honest claims, and better structure.

---

# 🌦️ Weather Forecast & Alert Application

> **Production-inspired Weather Intelligence System** built using scalable backend design patterns — featuring real-time forecasts, rule-based alerts, and an interactive dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square\&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square\&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?style=flat-square\&logo=streamlit)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey?style=flat-square\&logo=sqlite)


---

## 📌 Overview

This project simulates a **modular weather intelligence platform** similar to systems used in logistics, agriculture, and public safety domains.

It ingests real-time weather data from the free **Open-Meteo API**, processes it through a structured pipeline, generates alerts using a rule-based engine, and exposes data via REST APIs and a live dashboard.

---

## 🎯 Key Capabilities

* Real-time + forecast weather ingestion
* Structured data storage with relational schema
* Rule-based alert engine (RAIN / HEAT / WIND / UV)
* REST API layer with FastAPI
* Interactive dashboard with Streamlit
* Scheduled data refresh using APScheduler
* Notification support (Telegram / Email)
* Alert deduplication to avoid notification fatigue

---

## 🏗️ System Architecture

```
Open-Meteo API
      ↓
Data Ingestion (fetch + validate)
      ↓
Raw Storage (weather_raw)
      ↓
Processing Layer (transform → hourly/daily)
      ↓
Alert Engine (rule evaluation)
      ↓
alerts_log + Notification System
      ↓
FastAPI Backend (REST APIs)
      ↓
Streamlit Dashboard (UI)
```

---

## ⚙️ Tech Stack

| Layer           | Technology         |
| --------------- | ------------------ |
| Backend         | FastAPI, Uvicorn   |
| Database        | SQLite, SQLAlchemy |
| Data Processing | Python, Pandas     |
| Scheduler       | APScheduler        |
| Dashboard       | Streamlit, Plotly  |
| Notifications   | SMTP, Telegram API |
| Deployment      | Docker, Render     |

---

## 📁 Project Structure

```
weather-app/
├── api/              # FastAPI routes & schemas
├── src/              # ingestion + alert logic
├── db/               # database models & setup
├── jobs/             # scheduler jobs
├── notify/           # notification handlers
├── frontend/         # Streamlit dashboard
├── config.py         # configuration
├── main.py           # entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🚀 Getting Started

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Run Backend

```bash
uvicorn api.app:app --reload
```

### 3️⃣ Run Dashboard

```bash
streamlit run frontend/dashboard.py
```

### 4️⃣ Run Scheduler (optional)

```bash
python jobs/refresh.py
```

---

## 🔌 API Endpoints

| Endpoint                    | Description              |
| --------------------------- | ------------------------ |
| `/api/locations`            | List available locations |
| `/api/weather/current/{id}` | Latest weather           |
| `/api/forecast/hourly/{id}` | Hourly forecast          |
| `/api/forecast/daily/{id}`  | Daily forecast           |
| `/api/alerts`               | Recent alerts            |
| `/api/alerts/run/{id}`      | Trigger alert engine     |
| `/api/ingest/{id}`          | Fetch weather data       |

Swagger Docs:
👉 [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🚨 Alert Engine

The system uses a **rule-based alert engine** with:

* Threshold-based detection (temperature, rain, wind, UV)
* Severity classification (LOW → CRITICAL)
* Multi-condition alerts (e.g., rain + wind → storm)
* Deduplication using time window + severity

### Example Rules

| Alert | Condition          |
| ----- | ------------------ |
| HEAT  | Temperature ≥ 40°C |
| RAIN  | Probability > 60%  |
| WIND  | Gust ≥ 60 km/h     |
| UV    | Index ≥ 8          |

---

## ⏱️ Data Freshness

* Data refreshed every **3 hours**
* Latest values fetched using timestamp ordering
* Near real-time accuracy within API limits

---

## 🛡️ Failure Handling

* API response validation before processing
* Graceful handling of missing data
* Extendable retry logic for ingestion
* Alert deduplication prevents repeated notifications

---

## ⚠️ System Limitations

* SQLite (not suitable for high-concurrency production workloads)
* Single-node scheduler (no distributed job queue)
* Dependency on external API (no fallback provider)
* Rule-based alerts (no ML forecasting yet)

> Designed intentionally lightweight while following production-style architecture.

---

## 🐳 Deployment

### Docker

```bash
docker-compose up --build
```

### Cloud (Render)

* Connect GitHub repo
* Build: `pip install -r requirements.txt`
* Start: `uvicorn api.app:app --host 0.0.0.0 --port $PORT`

---

## 📊 Dashboard Preview

![Image](https://images.openai.com/static-rsc-4/kJJ5_E6HAgRAGi1MLp2jKMWwV4zHXwpC8fGcxzaVaDV6LYqrdTnU0txv2a5TM7onnj7YswmEwBdXvFr3iDGpxw9XttfcIKXqSipI3p8nq_WW3uziucggNeC6aDlCpGP30SIi9vOgLkCvCZVZN-VzY8ToAWZEluPRNmZQBELOsR6R6l_q8bUqdhAEGDqq8FNq?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/hQvHUL-tmq1DH0nqnX5YZnLDxNq5FCLxFvTLGx7K9c8UvnQGBh1lBewRAe-VzjsV6ejHBL-hAhofqcyNTaGJmvTSKQSAormxkQ36swzi_gynYGaFBYXWosvsPseMBi5OlzPK-YjuR3vxQGdExfABKCdSeaX-GQFNoC8856gaCtFqE-6sURp3vKn1tqD2NYiW?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/1Y79YjCCDiB31o3UGYw7pVxr3t5wyQ6X-QwG_UJZxhVgyGCUWkwOtQhw_X4V_t3CScCZwMKy1D8tpoWjprJPmHdMrdfqAsJbGTTNvlL3uLZ67VR9y2A17dyQINBrmRWOpjvXVmIV_GOlZsreJqM1noR6DOX5Jp_wWm6K80cziqN35QDzwFn7U-AN2Ux-A0p-?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/RCSIwyDGmc7P8ESHtlDDHIEqrKnvXbpu5yPX8SB8J08ABOPrN1B2-2egX9aRMIcq-FydNP5_rCgNpG1lsHfEjjzKqkpDeI7b4eGIhhQIWUAHhQ16OsyCz8FRZ4ORM39L3A1bMjWMAGDTkIjDMj3OaH56SCmdQrc2RwmGV2l0JRfy3qkCC_5bI9c3GNsua4sG?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/2NpsggAO7KanfustusU2qRRXljguPGbJc7ssLlvE97cvCFfJ6kMrFPoTn8fwY4STva23OojqHzWZudrCqlxGHE5gT5n-6SFr2ZKlvtgf2FVfdyFGlgWWjVKuUv_Bc7IGtJMyw8ZM3Mr_D6sQxNNbcXWqTVRepT0NAZTe2H15c9GRDmkK4s2btAxnSVW48j6G?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/ucF_fsHRxu_UtKrAFt4X5NsRaWLEYrGsD6chG6uMAvEkrzfR5ymDVZ4KuONBuu4ooY1YxHz31hkQbHMssV9KcZJb-ILq8YeNidEv9O0HzDh4T7QbP-HgRxiWtbSKw8szZd-xnhbYISCCxo4OnVyIur9GLO5kbFM250QJmEUN2VnKDUXEkojYVXH5rwOFTigq?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/qdzLSy6miYnjzN1Na-3dRLW7AwtGUEGzxZugA9oDo_SZOs9Ju_grBNplaDmfsKc_pu7D_klz_UA5dxXTkgdNYcHEfFG48IlpPX6vQjnQ4Zo3_FMjTLWj8QP_NfJAiCjB7ws47xozqmeFSh1F5DZZU99CxPS_pYwskXBDaRCdxIkYy9XaT2iUbGMM2ZG9rSVN?purpose=fullsize)

---

## 🧠 Design Decisions

* FastAPI for high-performance async-ready backend
* SQLite for simplicity and portability
* Modular architecture for easy scaling
* Rule-based alerts for deterministic behavior

---

## 🎤 Interview Talking Points

* Designed as a **data pipeline + alerting system**, not just a UI app
* Implemented **deduplication to avoid alert fatigue**
* Structured system into ingestion → processing → alert → API layers
* Easily scalable to PostgreSQL + Redis + Celery

---

## 🔮 Future Improvements

* Redis caching layer
* PostgreSQL migration
* ML-based forecasting
* Map visualization (Leaflet)
* Push notifications (mobile)



## 👨‍💻 Author

**Sarthak Dhumal**
Engineering Student | Backend & Data Enthusiast

---

## ⭐ Support

If this project helped you, consider giving it a star ⭐

---

