@echo off
REM Batch script to start the BIMTwinOps Python backend
REM Usage: start-backend.bat

echo Starting BIMTwinOps Backend Server...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Navigate to repo root
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Navigate to backend directory
cd backend

REM Check if .env file exists
if not exist ".env" (
    echo Note: .env file not found. Using defaults.
    echo Create backend\.env for custom configuration.
    echo.
)

REM Install/upgrade dependencies
echo Installing/updating dependencies...
python -m pip install --upgrade pip
python -m pip install -r api\requirements.txt

echo.
echo ========================================
echo Starting FastAPI server on port 8000...
echo API Documentation: http://localhost:8000/docs
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
