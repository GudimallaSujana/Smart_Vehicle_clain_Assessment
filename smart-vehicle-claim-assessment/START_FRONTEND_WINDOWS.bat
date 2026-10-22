@echo off
setlocal
cd /d "%~dp0frontend"

echo ============================================================
echo Starting Smart Vehicle Claim Assessment FRONTEND
echo URL: http://localhost:5173/
echo ============================================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found in PATH.
  echo Install Node.js LTS from https://nodejs.org/ and reopen this file.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo Installing frontend Node packages...
  call npm install
  if errorlevel 1 (
    echo ERROR: Frontend dependency installation failed.
    pause
    exit /b 1
  )
)

echo.
echo Frontend is starting. Keep this window open.
echo Website will be at: http://localhost:5173/
echo.
call npm run dev -- --host 127.0.0.1 --port 5173

echo.
echo Frontend stopped.
pause
