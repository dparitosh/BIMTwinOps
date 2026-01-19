@echo off
REM BIMTwinOps - Start Frontend Server
REM Usage: start-frontend.bat

echo.
echo Starting BIMTwinOps Frontend...
echo.

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Install from https://nodejs.org/
    pause
    exit /b 1
)

REM Navigate to frontend
cd /d "%~dp0pointcloud-frontend"

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing npm dependencies...
    npm install
)

REM Create .env if not exists
if not exist ".env" (
    echo Creating default .env file...
    (
        echo VITE_API_BASE_URL=http://localhost:8000
        echo VITE_APS_SERVICE_URL=http://localhost:3001
    ) > .env
)

echo.
echo ========================================
echo Vite Dev Server
echo ========================================
echo   URL: http://localhost:5173
echo ========================================
echo Press Ctrl+C to stop
echo.

npm run dev
