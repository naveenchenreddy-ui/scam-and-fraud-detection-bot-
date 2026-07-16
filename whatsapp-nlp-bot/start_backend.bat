@echo off
REM WhatsApp NLP Bot - Quick Start Script

echo.
echo ============================================
echo  WhatsApp NLP Bot - Starting Services
echo ============================================
echo.

REM Get the script directory
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [1/4] Checking virtual environment...
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -q -r backend\requirements.txt 2>nul

echo [4/4] Starting backend server...
echo.
echo ============================================
echo  Backend is starting on port 8000
echo ============================================
echo.
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.
echo Waiting for server to start...
echo.

cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
