@echo off
title RailTrack Passenger Streamlit Dashboard
echo ============================================================
echo   Starting RailTrack Passenger Dashboard (Port 8501)
echo ============================================================
echo.
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo Using Python: %PY%
echo Dashboard:    http://localhost:8501
echo.

%PY% -m streamlit run passenger_app.py --server.port 8501 --server.headless false

pause
