"""
============================================================
frontend/dashboard.py — Streamlit Weather Dashboard
============================================================
Run with: streamlit run frontend/dashboard.py
"""

import sys
import requests
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="Weather Forecast & Alert System",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #ffffff;
}

[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
    border-right: 1px solid rgba(255,255,255,0.1);
}

.metric-card {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s;
}

.metric-card:hover { transform: translateY(-3px); }
.metric-value { font-size: 2.2rem; font-weight: 700; color: #60a5fa; }
.metric-label { font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-top: 4px; }

.alert-card {
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    border-left: 5px solid;
}
.alert-CRITICAL { background: rgba(147,51,234,0.2); border-color: #9333ea; }
.alert-HIGH     { background: rgba(239,68,68,0.2);  border-color: #ef4444; }
.alert-MEDIUM   { background: rgba(245,158,11,0.2); border-color: #f59e0b; }
.alert-LOW      { background: rgba(34,197,94,0.2);  border-color: #22c55e; }

.weather-icon { font-size: 3.5rem; margin-bottom: 8px; }
.current-temp { font-size: 3rem; font-weight: 700; color: #fbbf24; }
.section-title {
    font-size: 1.3rem; font-weight: 600;
    border-bottom: 2px solid rgba(96,165,250,0.4);
    padding-bottom: 8px; margin: 20px 0 15px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"

WEATHER_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️", 51: "🌦️", 53: "🌧️",
    55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌊",
    71: "❄️", 73: "❄️", 75: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

SEVERITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}


# ── API Helpers ───────────────────────────────────────────
@st.cache_data(ttl=300)
def api_get(endpoint: str):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        return None
    except Exception:
        return None


def api_post(endpoint: str):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌦️ Weather App")
    st.markdown("---")

    locations_data = api_get("/api/locations")
    if not locations_data:
        st.error("❌ API offline. Start FastAPI first:\n`uvicorn api.app:app --reload`")
        st.stop()

    city_map = {loc["city"]: loc["id"] for loc in locations_data}
    city_names = list(city_map.keys())

    selected_city = st.selectbox("📍 Select City", city_names, key="city_select")
    location_id = city_map[selected_city]

    st.markdown("---")
    st.markdown("### ⚙️ Actions")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("Fetching weather..."):
                result = api_post(f"/api/ingest/{location_id}")
                if result:
                    st.success(f"✅ {result.get('hourly_records', 0)} hourly records updated")
                    st.cache_data.clear()

    with col2:
        if st.button("🚨 Run Alerts", use_container_width=True):
            with st.spinner("Running engine..."):
                result = api_post(f"/api/alerts/run/{location_id}")
                if result is not None:
                    st.success(f"✅ {len(result)} new alerts")
                    st.cache_data.clear()

    st.markdown("---")
    st.markdown("### 📊 Quick Summary")
    summary = api_get("/api/summary")
    if summary:
        st.metric("Total Locations", summary.get("total_locations", 0))
        st.metric("Alerts (48h)", summary.get("alerts_last_48h", 0))
        last_refresh = summary.get("last_data_refresh")
        if last_refresh:
            dt = datetime.fromisoformat(last_refresh.replace("Z", ""))
            st.caption(f"Last refresh:\n{dt.strftime('%d %b %H:%M UTC')}")

    st.markdown("---")
    st.caption("Powered by Open-Meteo API 🌐")


# ── Main Content ──────────────────────────────────────────
st.markdown(f"# 🌦️ {selected_city} Weather Dashboard")
st.markdown(f"`{datetime.utcnow().strftime('%A, %d %B %Y • %H:%M UTC')}`")

# ── Current Weather ───────────────────────────────────────
current = api_get(f"/api/weather/current/{location_id}")

if current:
    st.markdown('<div class="section-title">🌡️ Current Conditions</div>', unsafe_allow_html=True)
    wcode = None
    icon = WEATHER_ICONS.get(wcode, "🌡️")
    desc = current.get("weather_description", "N/A")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = [
        (c1, "🌡️ Temperature", f"{current.get('temperature', 'N/A')}°C", None),
        (c2, "🤔 Feels Like", f"{current.get('feels_like', 'N/A')}°C", None),
        (c3, "💧 Humidity", f"{current.get('humidity', 'N/A')}%", None),
        (c4, "💨 Wind", f"{current.get('wind_speed', 'N/A')} km/h", None),
        (c5, "☀️ UV Index", f"{current.get('uv_index', 'N/A')}", None),
        (c6, "🌧️ Rain Prob", f"{current.get('precipitation_prob', 'N/A')}%", None),
    ]
    for col, label, val, delta in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"<center><small>🌤️ {desc}</small></center>", unsafe_allow_html=True)
    st.markdown("")
else:
    st.warning("⚠️ No current weather data. Click **🔄 Refresh Data** in the sidebar.")


# ── Tabs for Charts / Alerts ──────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Hourly Forecast", "📅 7-Day Forecast", "🚨 Alerts"])


# ── TAB 1: Hourly Forecast ────────────────────────────────
with tab1:
    hourly = api_get(f"/api/forecast/hourly/{location_id}?hours=48")
    if hourly:
        df = pd.DataFrame(hourly)
        df["forecast_time"] = pd.to_datetime(df["forecast_time"])

        # Temperature Chart
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=df["forecast_time"], y=df["temperature_2m"],
            name="Temperature (°C)", line=dict(color="#fbbf24", width=2.5),
            fill="tozeroy", fillcolor="rgba(251,191,36,0.1)",
            mode="lines+markers", marker=dict(size=4),
        ))
        fig_temp.add_trace(go.Scatter(
            x=df["forecast_time"], y=df["apparent_temp"],
            name="Feels Like (°C)", line=dict(color="#60a5fa", width=2, dash="dot"),
            mode="lines",
        ))
        fig_temp.update_layout(
            title="Temperature Forecast (48h)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font=dict(color="white"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            yaxis_title="°C",
            height=350,
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        col_left, col_right = st.columns(2)

        # Rain Probability Chart
        with col_left:
            fig_rain = go.Figure()
            fig_rain.add_trace(go.Bar(
                x=df["forecast_time"], y=df["precipitation_prob"],
                name="Rain Probability (%)",
                marker=dict(
                    color=df["precipitation_prob"],
                    colorscale=[[0, "#22c55e"], [0.6, "#f59e0b"], [1, "#3b82f6"]],
                ),
            ))
            fig_rain.add_hline(
                y=60, line_dash="dash", line_color="#ef4444",
                annotation_text="Alert Threshold (60%)",
                annotation_font_color="#ef4444",
            )
            fig_rain.update_layout(
                title="Rain Probability (%)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.03)",
                font=dict(color="white"),
                height=300,
            )
            st.plotly_chart(fig_rain, use_container_width=True)

        # Wind Chart
        with col_right:
            fig_wind = go.Figure()
            fig_wind.add_trace(go.Scatter(
                x=df["forecast_time"], y=df["wind_speed_10m"],
                name="Wind Speed", line=dict(color="#a78bfa", width=2),
                fill="tozeroy", fillcolor="rgba(167,139,250,0.1)",
            ))
            fig_wind.add_trace(go.Scatter(
                x=df["forecast_time"], y=df["wind_gusts_10m"],
                name="Gusts", line=dict(color="#f87171", width=2, dash="dot"),
            ))
            fig_wind.add_hline(
                y=60, line_dash="dash", line_color="#ef4444",
                annotation_text="Gust Alert (60 km/h)",
                annotation_font_color="#ef4444",
            )
            fig_wind.update_layout(
                title="Wind Speed & Gusts (km/h)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.03)",
                font=dict(color="white"),
                height=300,
            )
            st.plotly_chart(fig_wind, use_container_width=True)

        # UV Index Chart
        fig_uv = go.Figure()
        fig_uv.add_trace(go.Bar(
            x=df["forecast_time"], y=df["uv_index"],
            name="UV Index",
            marker=dict(
                color=df["uv_index"],
                colorscale="RdYlGn_r",
                showscale=True,
                colorbar=dict(title="UV", tickfont=dict(color="white")),
            ),
        ))
        fig_uv.add_hline(y=8, line_dash="dash", line_color="#9333ea",
                         annotation_text="UV Alert Threshold (8)", annotation_font_color="#9333ea")
        fig_uv.update_layout(
            title="UV Index Forecast",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font=dict(color="white"), height=280,
        )
        st.plotly_chart(fig_uv, use_container_width=True)

    else:
        st.info("📡 No hourly data. Click **🔄 Refresh Data** in the sidebar.")


# ── TAB 2: 7-Day Forecast ─────────────────────────────────
with tab2:
    daily = api_get(f"/api/forecast/daily/{location_id}?days=7")
    if daily:
        df_d = pd.DataFrame(daily)
        df_d["forecast_date"] = pd.to_datetime(df_d["forecast_date"])
        df_d["day_label"] = df_d["forecast_date"].dt.strftime("%a\n%d %b")

        # Min-Max temperature range
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(
            x=df_d["day_label"], y=df_d["temp_max"],
            name="Max Temp", line=dict(color="#f87171", width=3),
            mode="lines+markers+text",
            text=[f"{v:.0f}°" for v in df_d["temp_max"]],
            textposition="top center", textfont=dict(color="#f87171"),
        ))
        fig_daily.add_trace(go.Scatter(
            x=df_d["day_label"], y=df_d["temp_min"],
            name="Min Temp", line=dict(color="#60a5fa", width=3),
            fill="tonexty", fillcolor="rgba(96,165,250,0.15)",
            mode="lines+markers+text",
            text=[f"{v:.0f}°" for v in df_d["temp_min"]],
            textposition="bottom center", textfont=dict(color="#60a5fa"),
        ))
        fig_daily.update_layout(
            title="7-Day Temperature Range (°C)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font=dict(color="white"), height=380,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_daily, use_container_width=True)

        # Daily summary table
        st.markdown('<div class="section-title">📋 Daily Summary</div>', unsafe_allow_html=True)
        cols = st.columns(len(df_d))
        for i, (col, (_, row)) in enumerate(zip(cols, df_d.iterrows())):
            with col:
                wcode = int(row["weather_code"]) if pd.notna(row.get("weather_code")) else 0
                icon = WEATHER_ICONS.get(wcode, "🌡️")
                uv = row.get("uv_index_max", 0) or 0
                rain_p = row.get("precipitation_prob_max", 0) or 0
                st.markdown(f"""
                <div class="metric-card" style="padding:12px;">
                    <div style="font-size:1.8rem;">{icon}</div>
                    <div style="font-size:0.85rem;font-weight:600;color:#94a3b8;">
                        {row['forecast_date'].strftime('%a %d %b')}
                    </div>
                    <div style="color:#f87171;font-weight:700;">{row.get('temp_max','N/A'):.0f}°</div>
                    <div style="color:#60a5fa;font-weight:700;">{row.get('temp_min','N/A'):.0f}°</div>
                    <div style="font-size:0.75rem;color:#94a3b8;margin-top:6px;">
                        🌧 {rain_p:.0f}% · ☀️ UV {uv:.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📡 No daily data. Click **🔄 Refresh Data** in the sidebar.")


# ── TAB 3: Alerts ─────────────────────────────────────────
with tab3:
    alerts = api_get(f"/api/alerts/{location_id}?hours=48")
    all_alerts = api_get("/api/alerts?hours=48")

    st.markdown('<div class="section-title">🚨 Active Weather Alerts</div>', unsafe_allow_html=True)

    if not alerts:
        st.success("✅ No active alerts for this location in the last 48 hours.")
    else:
        for alert in alerts:
            sev = alert["severity"]
            icon = {"RAIN": "🌧️", "HEAT": "🌡️", "WIND": "💨", "UV": "☀️"}.get(alert["alert_type"], "⚠️")
            sem = SEVERITY_EMOJI.get(sev, "⚠️")
            st.markdown(f"""
            <div class="alert-card alert-{sev}">
                <strong>{icon} {alert['title']} &nbsp; {sem} {sev}</strong><br/>
                <small>Type: {alert['alert_type']} | 
                Value: {alert.get('trigger_value','N/A')} | 
                Threshold: {alert.get('threshold_used','N/A')}</small><br/>
                <p style="margin:8px 0 0 0;font-size:0.9rem;">{alert['message']}</p>
                <small style="color:rgba(255,255,255,0.5);">
                    Generated: {datetime.fromisoformat(alert['alert_time'].replace('Z','')).strftime('%d %b %H:%M UTC')}
                </small>
            </div>
            """, unsafe_allow_html=True)

    # All locations alert heatmap
    if all_alerts:
        st.markdown('<div class="section-title">📊 Alert Distribution (All Cities)</div>', unsafe_allow_html=True)
        df_alerts = pd.DataFrame(all_alerts)
        if not df_alerts.empty:
            locs_data = {loc["id"]: loc["city"] for loc in (locations_data or [])}
            df_alerts["city"] = df_alerts["location_id"].map(locs_data).fillna("Unknown")

            col_a, col_b = st.columns(2)
            with col_a:
                count_by_type = df_alerts["alert_type"].value_counts().reset_index()
                count_by_type.columns = ["Type", "Count"]
                fig_pie = px.pie(count_by_type, names="Type", values="Count",
                                 title="Alerts by Type",
                                 color_discrete_sequence=["#3b82f6","#ef4444","#a78bfa","#fbbf24"])
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_b:
                count_by_sev = df_alerts["severity"].value_counts().reset_index()
                count_by_sev.columns = ["Severity", "Count"]
                colors = {"CRITICAL":"#9333ea","HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#22c55e"}
                fig_bar = px.bar(count_by_sev, x="Severity", y="Count",
                                 title="Alerts by Severity",
                                 color="Severity",
                                 color_discrete_map=colors)
                fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(255,255,255,0.03)",
                                      font=dict(color="white"), showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

# ── Footer ────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><small>🌦️ Weather Forecast & Alert System | "
    "Data: Open-Meteo API | Built with FastAPI + Streamlit</small></center>",
    unsafe_allow_html=True,
)
