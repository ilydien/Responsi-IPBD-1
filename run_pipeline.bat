@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Running Wired Articles Pipeline
echo ==========================================

echo.
echo [1/4] Running Selenium Scraper...
python scripts\scraper.py

echo.
echo [2/4] Starting FastAPI in background...
start "API Server" python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
timeout /t 5 /nobreak >nul

echo.
echo [3/4] Running Prefect DAG...
python scripts\dag.py

echo.
echo [4/4] Running SQL Queries...
python scripts\queries.py

echo.
echo ==========================================
echo Pipeline completed successfully!
echo ==========================================

taskkill /f /im uvicorn.exe 2>nul
exit /b 0