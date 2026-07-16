@echo off
REM WhatsApp NLP Bot - Startup Script for Windows

setlocal enabledelayedexpansion

echo.
echo 🚀 WhatsApp NLP Bot Startup Script
echo ===================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo   Please install Python 3.11+ from https://www.python.org
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed or not in PATH
    echo   Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo ✅ Python and Node.js found

REM Backend setup
echo.
echo 🐍 Setting up Python backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo.
    echo ⚠️  .env file not found
    echo Creating from .env.example...
    copy .env.example .env
    echo ⚠️  Please edit backend\.env with your Twilio credentials
)

cd ..

REM Frontend setup
echo.
echo 📦 Setting up React frontend...
cd frontend

if not exist "node_modules" (
    echo Installing Node dependencies...
    call npm install -q
)

cd ..

REM Start services
echo.
echo 🎯 Starting services...
echo ====================

REM Start FastAPI
echo Starting FastAPI server...
cd backend
call venv\Scripts\activate.bat
start "FastAPI" python -m uvicorn main:app --reload --port 8000
cd ..
echo ✓ FastAPI started
echo   📚 Docs: http://localhost:8000/docs

REM Start React
echo Starting React dashboard...
cd frontend
start "React" npm run dev
cd ..
echo ✓ React started
echo   🖥️  Dashboard: http://localhost:3000

echo.
echo ✅ All services started!
echo ========================
echo.
echo 📋 Services:
echo   • FastAPI Backend: http://localhost:8000
echo   • React Dashboard: http://localhost:3000
echo.
echo 📚 Documentation:
echo   • API Swagger: http://localhost:8000/docs
echo   • API ReDoc: http://localhost:8000/redoc
echo.
echo ⚠️  Make sure MongoDB is running separately!
echo   Command: mongod
echo.
echo.
pause

endlocal
