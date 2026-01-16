@echo off
REM Batch script to start the BIMTwinOps React frontend
REM Usage: start-frontend.bat

echo Starting BIMTwinOps Frontend...

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Display versions
echo Node version:
node --version
echo npm version:
npm --version
echo.

REM Navigate to frontend directory
cd /d "%~dp0pointcloud-frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    npm install
)

echo.
echo ========================================
echo Starting Vite dev server...
echo Frontend: http://localhost:5173
echo Press Ctrl+C to stop
echo ========================================
echo.

npm run dev
