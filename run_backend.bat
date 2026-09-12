@echo off
title RailTrack FastAPI Backend Server
echo ============================================================
echo   Starting RailTrack FastAPI Backend Server (Port 8000)
echo ============================================================
echo.
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo Using Python: %PY%
echo Backend URL:  http://localhost:8000
echo Swagger Docs: http://localhost:8000/docs
echo.

%PY% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
