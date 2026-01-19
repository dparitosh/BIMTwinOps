@echo off
REM BIMTwinOps - Stop All Services
REM Usage: stop-all.bat
REM
REM Port configuration (read from .env or use defaults):
REM   BACKEND_PORT (default: 8000)
REM   FRONTEND_PORT (default: 5173) 
REM   APS_SERVICE_PORT (default: 3001)

setlocal enabledelayedexpansion

REM Default ports
set BACKEND_PORT=8000
set FRONTEND_PORT=5173
set APS_PORT=3001

REM Try to read BACKEND_PORT from backend\.env
if exist "%~dp0backend\.env" (
    for /f "tokens=1,* delims==" %%a in ('findstr /i "BACKEND_PORT" "%~dp0backend\.env"') do (
        set "line=%%b"
        for /f "tokens=1" %%c in ("!line!") do set BACKEND_PORT=%%c
    )
    for /f "tokens=1,* delims==" %%a in ('findstr /i "APS_SERVICE_PORT" "%~dp0backend\.env"') do (
        set "line=%%b"
        for /f "tokens=1" %%c in ("!line!") do set APS_PORT=%%c
    )
)

echo.
echo ======================================
echo   Stopping BIMTwinOps Services
echo ======================================
echo   Backend port:  %BACKEND_PORT%
echo   Frontend port: %FRONTEND_PORT%
echo   APS port:      %APS_PORT%
echo.

REM Stop processes on backend port
echo Checking for backend on port %BACKEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Stop processes on frontend port
echo Checking for frontend on port %FRONTEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Stop processes on APS service port
echo Checking for APS service on port %APS_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%APS_PORT%.*LISTENING"') do (
    echo Stopping PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Services stopped.
echo.
endlocal
pause
