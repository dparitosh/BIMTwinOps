@echo off
REM BIMTwinOps - Stop All Services
REM Usage: stop-all.bat

echo.
echo ======================================
echo   Stopping BIMTwinOps Services
echo ======================================
echo.

REM Stop processes on backend port 8000
echo Checking for backend on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Stop processes on frontend port 5173
echo Checking for frontend on port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Stop processes on APS service port 3001
echo Checking for APS service on port 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Services stopped.
echo.
pause
