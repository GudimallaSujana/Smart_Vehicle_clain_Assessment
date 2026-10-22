@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ============================================================
echo AI-Based Smart Vehicle Claim Assessment - Local Launcher
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python is not installed or not added to PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add Python to PATH" during install.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js / npm is not installed or not added to PATH.
  echo Install Node.js LTS from https://nodejs.org/
  pause
  exit /b 1
)

echo Starting backend and frontend in separate windows...
echo Please keep both new terminal windows open.
echo.

start "Smart Claim Backend - localhost 8000" "%ROOT%START_BACKEND_WINDOWS.bat"

echo Waiting briefly before starting frontend...
timeout /t 4 /nobreak >nul

start "Smart Claim Frontend - localhost 5173" "%ROOT%START_FRONTEND_WINDOWS.bat"

echo Waiting for startup...
timeout /t 8 /nobreak >nul

echo Opening the website...
start "" "http://localhost:5173/"

echo.
echo If the browser still says connection refused, wait 30-60 seconds.
echo Then refresh http://localhost:5173/
echo.
echo Local links:
echo   Website:  http://localhost:5173/
echo   API Docs: http://localhost:8000/docs
echo.
echo If it fails, copy the error text from the two terminal windows and send it here.
echo.
pause
