@echo off
echo ============================================================
echo   Weather Forecast ^& Alert Application - Quick Start
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b
)

:: Install dependencies if needed
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    echo [2/4] Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate.bat
)

:: Create logs directory
if not exist "logs" mkdir logs

echo [3/4] Starting FastAPI backend...
start "FastAPI Backend" cmd /k "call venv\Scripts\activate.bat && uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 4 /nobreak >nul

echo [4/4] Starting Streamlit dashboard...
start "Streamlit Dashboard" cmd /k "call venv\Scripts\activate.bat && streamlit run frontend/dashboard.py --server.port 8501"

echo.
echo ============================================================
echo   FastAPI  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo   Dashboard: http://localhost:8501
echo ============================================================
echo.
echo Both windows are opening. Press any key to exit this window.
pause >nul
