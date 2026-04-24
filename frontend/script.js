const API_BASE = 'http://127.0.0.1:8000/api';
let chartInstance = null;

// Utility: Show Toast
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = isError ? 'show error' : 'show';
    setTimeout(() => { toast.className = toast.className.replace('show', ''); }, 3000);
}

// Utility: Show/Hide Loader
function toggleLoader(show, text = 'Loading...') {
    document.getElementById('loader-text').textContent = text;
    if(show) document.getElementById('loader').classList.add('active');
    else document.getElementById('loader').classList.remove('active');
}

// Update Clock
setInterval(() => {
    document.getElementById('current-time').textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}, 1000);

// Fetch Locations & Init
async function init() {
    try {
        const res = await fetch(`${API_BASE}/locations`);
        if (!res.ok) throw new Error('API Offline');
        const locations = await res.json();
        
        const select = document.getElementById('city-select');
        locations.forEach(loc => {
            const opt = document.createElement('option');
            opt.value = loc.id;
            opt.textContent = `${loc.city}, ${loc.country}`;
            select.appendChild(opt);
        });

        if(locations.length > 0) {
            loadCityData();
        }
    } catch (err) {
        showToast('Cannot connect to FastAPI Backend. Is it running?', true);
    }
}

// Load City Data
async function loadCityData() {
    const locId = document.getElementById('city-select').value;
    const cityName = document.getElementById('city-select').options[document.getElementById('city-select').selectedIndex].text.split(',')[0];
    
    document.getElementById('display-city').textContent = cityName;
    toggleLoader(true, `Fetching data for ${cityName}...`);

    try {
        // 1. Fetch Current
        const currentRes = await fetch(`${API_BASE}/weather/current/${locId}`);
        if (currentRes.ok) {
            const current = await currentRes.json();
            document.getElementById('val-temp').innerHTML = `${current.temperature ?? '--'}<span>°C</span>`;
            document.getElementById('val-humidity').innerHTML = `${current.humidity ?? '--'}<span>%</span>`;
            document.getElementById('val-wind').innerHTML = `${current.wind_speed ?? '--'}<span>km/h</span>`;
            document.getElementById('val-rain').innerHTML = `${current.precipitation_prob ?? '--'}<span>%</span>`;
            document.getElementById('val-uv').innerHTML = `${current.uv_index ?? '--'}`;
            document.getElementById('display-desc').innerHTML = `<i class="fa-solid fa-cloud"></i> ${current.weather_description} (Feels like ${current.feels_like}°C)`;
            
            const updateTime = new Date(current.last_updated + 'Z');
            document.getElementById('last-update-time').textContent = updateTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        } else {
            resetMetrics();
            document.getElementById('display-desc').innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:var(--accent-red)"></i> No data available. Click "Fetch Latest Data".`;
        }

        // 2. Fetch Hourly for Chart
        const hourlyRes = await fetch(`${API_BASE}/forecast/hourly/${locId}?hours=48`);
        if (hourlyRes.ok) {
            const hourlyData = await hourlyRes.json();
            renderChart(hourlyData);
        }

        // 3. Fetch Alerts
        const alertsRes = await fetch(`${API_BASE}/alerts/${locId}?hours=48`);
        if (alertsRes.ok) {
            const alerts = await alertsRes.json();
            renderAlerts(alerts);
        }

    } catch (err) {
        console.error(err);
        showToast('Error loading data', true);
    } finally {
        toggleLoader(false);
    }
}

function resetMetrics() {
    ['temp', 'humidity', 'wind', 'rain', 'uv'].forEach(id => {
        document.getElementById(`val-${id}`).innerHTML = `--`;
    });
    if(chartInstance) chartInstance.destroy();
}

// Render Chart.js Chart
function renderChart(data) {
    const ctx = document.getElementById('weatherChart').getContext('2d');
    
    const labels = data.map(d => {
        const date = new Date(d.forecast_time + 'Z');
        return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    });
    
    const temps = data.map(d => d.temperature_2m);
    const rainProbs = data.map(d => d.precipitation_prob);

    if(chartInstance) chartInstance.destroy();

    Chart.defaults.color = 'rgba(255, 255, 255, 0.7)';
    Chart.defaults.font.family = 'Inter';

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: temps,
                    borderColor: '#fbbf24',
                    backgroundColor: 'rgba(251, 191, 36, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Rain Prob (%)',
                    data: rainProbs,
                    type: 'bar',
                    backgroundColor: 'rgba(96, 165, 250, 0.3)',
                    borderColor: '#60a5fa',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { maxTicksLimit: 12 } },
                y: { type: 'linear', display: true, position: 'left', grid: { color: 'rgba(255,255,255,0.05)' } },
                y1: { type: 'linear', display: true, position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false } }
            },
            plugins: {
                legend: { position: 'top' }
            }
        }
    });
}

// Render Alerts
function renderAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    const countBadge = document.getElementById('alert-count');
    
    // Filter active alerts
    const activeAlerts = alerts.filter(a => a.is_active);
    countBadge.textContent = activeAlerts.length;

    if (activeAlerts.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 30px 10px; color: var(--text-muted);">
                <i class="fa-solid fa-shield-check" style="font-size: 2.5rem; margin-bottom: 10px; color: var(--accent-green);"></i>
                <p>All clear! No active alerts for this location.</p>
            </div>`;
        return;
    }

    let html = '';
    const icons = { 'RAIN': 'fa-cloud-showers-heavy', 'HEAT': 'fa-temperature-arrow-up', 'WIND': 'fa-wind', 'UV': 'fa-sun' };

    activeAlerts.forEach(alert => {
        const icon = icons[alert.alert_type] || 'fa-triangle-exclamation';
        html += `
        <div class="alert-item alert-${alert.severity}">
            <div class="alert-header">
                <div class="alert-title"><i class="fa-solid ${icon}"></i> ${alert.title}</div>
                <div class="alert-badge badge-${alert.severity}">${alert.severity}</div>
            </div>
            <div class="alert-msg">${alert.message}</div>
        </div>`;
    });

    container.innerHTML = html;
}

// Action: Ingest Data
async function triggerIngest() {
    const locId = document.getElementById('city-select').value;
    toggleLoader(true, 'Fetching latest weather from Open-Meteo API...');
    try {
        const res = await fetch(`${API_BASE}/ingest/${locId}`, { method: 'POST' });
        if (res.ok) {
            showToast('Data refreshed successfully!');
            await loadCityData(); // reload dashboard
        } else {
            throw new Error('Ingest failed');
        }
    } catch (err) {
        showToast('Failed to fetch data', true);
    } finally {
        toggleLoader(false);
    }
}

// Action: Run Alerts
async function triggerAlerts() {
    const locId = document.getElementById('city-select').value;
    toggleLoader(true, 'Running Alert Engine Rules...');
    try {
        const res = await fetch(`${API_BASE}/alerts/run/${locId}`, { method: 'POST' });
        if (res.ok) {
            const newAlerts = await res.json();
            showToast(`Alert Engine Complete. Generated ${newAlerts.length} new alerts.`);
            await loadCityData(); // reload to show new alerts
        } else {
            throw new Error('Engine failed');
        }
    } catch (err) {
        showToast('Failed to run alert engine', true);
    } finally {
        toggleLoader(false);
    }
}

// Start
window.addEventListener('DOMContentLoaded', init);
