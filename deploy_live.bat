@echo off
title RailTrack - 1-Click Live Public Deployment
echo ============================================================
echo   RailTrack - Live Deployment & Public HTTPS Tunnels
echo ============================================================
echo.
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "RailTrack Backend" /min %PY% -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo [*] Starting Streamlit Passenger App on http://127.0.0.1:8501 ...
start "RailTrack Passenger App" /min %PY% -m streamlit run passenger_app.py --server.port 8501 --server.headless true

timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo   Generating Live Public HTTPS URL via Cloudflare Edge...
echo ============================================================
echo.
.\cloudflared.exe tunnel --protocol http2 --edge-ip-version 4 --url http://127.0.0.1:8501
pause
