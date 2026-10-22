@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or newer from python.org first, including the Python Launcher.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  pause
  exit /b 1
)
if not exist .env .venv\Scripts\python.exe -m app.manage setup
if not exist .env (
  pause
  exit /b 1
)
echo Open http://localhost:8000 for the website and http://localhost:8000/admin for the admin.
echo Press Ctrl+C to stop the local server.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
