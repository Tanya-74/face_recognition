@echo off
rem Activates the virtual environment, starts the server and opens the browser.
rem Double-click this file.
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo The app is not installed yet. Follow "Install" in README.md first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
set PYTHONUTF8=1
rem open the browser after 4 seconds (gives the server time to start)
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
echo Starting... keep this window open while you use the app. Close it to stop the app.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
