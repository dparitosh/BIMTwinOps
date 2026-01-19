@echo off
REM BIMTwinOps - Start Backend Server
REM Usage: start-backend.bat

echo.
echo Starting BIMTwinOps Backend...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Navigate to repo root
cd /d "%~dp0"

REM Create venv if not exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Navigate to backend
cd backend

REM Install dependencies
python -m pip install --upgrade pip --quiet
python -m pip install -r api\requirements.txt --quiet

echo.
echo ========================================
echo FastAPI Server
echo ========================================
echo   API URL:  http://127.0.0.1:8000
echo   Docs:     http://127.0.0.1:8000/docs
echo   GraphQL:  http://127.0.0.1:8000/api/graphql
echo ========================================
echo Press Ctrl+C to stop
echo.

python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
