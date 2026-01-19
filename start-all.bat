@echo off
REM BIMTwinOps - Start All Services
REM Usage: start-all.bat
REM
REM Port configuration (read from .env or use defaults):
REM   BACKEND_PORT (default: 8000)
REM   FRONTEND_PORT (default: 5173)

setlocal enabledelayedexpansion

REM Default ports
set BACKEND_PORT=8000
set FRONTEND_PORT=5173

REM Try to read BACKEND_PORT from backend\.env
if exist "%~dp0backend\.env" (
    for /f "tokens=1,* delims==" %%a in ('findstr /i "BACKEND_PORT" "%~dp0backend\.env"') do (
        set "line=%%b"
        for /f "tokens=1" %%c in ("!line!") do set BACKEND_PORT=%%c
    )
)

echo.
echo ======================================
echo   Starting BIMTwinOps Services
echo ======================================
echo.

REM Start backend in new window
echo Starting Backend Server...
start "BIMTwinOps Backend" cmd /k "%~dp0start-backend.bat"

REM Wait for backend
echo Waiting for backend to start (3s)...
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting Frontend Server...
start "BIMTwinOps Frontend" cmd /k "%~dp0start-frontend.bat"

echo.
echo ======================================
echo   Services Started!
echo ======================================
echo.
echo   Backend API: http://localhost:%BACKEND_PORT%
echo   API Docs:    http://localhost:%BACKEND_PORT%/docs
echo   Frontend:    http://localhost:%FRONTEND_PORT%
echo.
echo To stop: Close the command windows
echo      or: stop-all.bat
echo.
endlocal
pause
