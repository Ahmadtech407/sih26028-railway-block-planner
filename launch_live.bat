@echo off
title RailTrack Live Deployment Launcher
echo =======================================================
echo         RailTrack - Live Deployment & Tunnel
echo =======================================================
echo.

cd /d " %~dp0\

:: Check if virtual environment exists
if exist .venv\Scripts\python.exe (
 set PYTHON=.venv\Scripts\python.exe
) else (
 set PYTHON=python
)

:: 1. Start FastAPI backend in background if not listening on port 8000
netstat -ano | findstr /R /C:\:8000 *LISTENING\ >nul
if errorlevel 1 (
 echo [*] Starting FastAPI Backend on port 8000...
 start /B \\ %PYTHON% -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
 timeout /t 2 /nobreak >nul
) else (
 echo [*] FastAPI Backend already running on port 8000.
)

:: 2. Start Streamlit passenger app in background if not listening on port 8501
netstat -ano | findstr /R /C:\:8501 *LISTENING\ >nul
if errorlevel 1 (
 echo [*] Starting Streamlit Passenger App on port 8501...
 start /B \\ %PYTHON% -m streamlit run passenger_app.py --server.port 8501 --server.headless true --server.runOnSave true
 timeout /t 3 /nobreak >nul
) else (
 echo [*] Streamlit already running on port 8501.
)

echo.
echo =======================================================
echo Local Wi-Fi Access (Fastest for phone on same Wi-Fi):
echo http://10.187.237.181:8501
echo.
echo Generating Secure Public HTTPS Link via OpenSSH...
echo =======================================================
ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8501 nokey@localhost.run
pause
