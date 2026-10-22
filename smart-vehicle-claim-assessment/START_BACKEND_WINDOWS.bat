@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo Starting Smart Vehicle Claim Assessment BACKEND
echo URL: http://localhost:8000/docs
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found in PATH.
  echo Install Python 3.10+ and tick "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create Python virtual environment.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo Installing backend Python packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Backend dependency installation failed.
  pause
  exit /b 1
)

echo.
echo Backend is starting. Keep this window open.
echo API Docs will be at: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

echo.
echo Backend stopped.
pause
