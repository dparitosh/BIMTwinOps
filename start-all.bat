@echo off
REM BIMTwinOps - Start All Services
REM Usage: start-all.bat

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
echo   Backend API: http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Frontend:    http://localhost:5173
echo.
echo To stop: Close the command windows
echo      or: stop-all.bat
echo.
pause
