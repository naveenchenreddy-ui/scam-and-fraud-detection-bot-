#!/bin/bash

# WhatsApp NLP Bot - Startup Script
# This script starts all required services

set -e

echo "🚀 WhatsApp NLP Bot Startup Script"
echo "=================================="

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo ""
    echo "Would you like to use Docker Compose? (y/n)"
    read -r use_docker
    
    if [ "$use_docker" = "y" ]; then
        echo ""
        echo "📦 Starting services with Docker Compose..."
        docker-compose up --build
        exit 0
    fi
fi

echo ""
echo "📋 Manual Setup Mode"
echo "===================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

echo ""
echo "✅ All required tools are installed"

# Create Python virtual environment
echo ""
echo "🐍 Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found in backend/"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "   ⚠️  Please edit backend/.env with your Twilio credentials"
fi

cd ..

# Setup Node frontend
echo ""
echo "📦 Setting up React frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install -q
fi

cd ..

# Start services in background
echo ""
echo "🎯 Starting services..."
echo "===================="

# Start FastAPI (background)
echo "Starting FastAPI server..."
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "   ✓ FastAPI started (PID: $BACKEND_PID)"
echo "   📚 Docs: http://localhost:8000/docs"

# Start React (background)
echo "Starting React dashboard..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   ✓ React started (PID: $FRONTEND_PID)"
echo "   🖥️  Dashboard: http://localhost:3000"

echo ""
echo "✅ All services started!"
echo "========================"
echo ""
echo "📋 Services:"
echo "   • FastAPI Backend: http://localhost:8000"
echo "   • React Dashboard: http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "   • API Swagger: http://localhost:8000/docs"
echo "   • API ReDoc: http://localhost:8000/redoc"
echo ""
echo "📝 Logs:"
echo "   • Backend: backend.log"
echo "   • Frontend: frontend.log"
echo ""
echo "❌ To stop all services, run:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait for any service to finish
wait
