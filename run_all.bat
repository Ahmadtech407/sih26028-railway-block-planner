@echo off
title RailTrack - Launch All Services
echo ============================================================
echo   Launching RailTrack Backend & Frontend Services
echo ============================================================
echo.
cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "RailTrack Backend (FastAPI)" run_backend.bat

echo Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak >nul

echo [2/2] Starting Streamlit Passenger Dashboard on http://localhost:8501 ...
start "RailTrack Frontend (Streamlit)" run_frontend.bat

echo.
echo ============================================================
echo   Both services are starting in separate windows!
echo   - Backend Docs:  http://localhost:8000/docs
echo   - Passenger App: http://localhost:8501
echo ============================================================
echo.
pause
