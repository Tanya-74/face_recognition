@echo off
rem Activates the virtual environment, gets the face models if they are missing,
rem starts the server and opens the browser. Double-click this file.
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo The app is not installed yet. Follow "Install" in README.md first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
set PYTHONUTF8=1

rem First start only: download the two model files into the models folder. Needs internet this one time.
set NEED_MODELS=0
if not exist "models\arcface_resnet.onnx" set NEED_MODELS=1
if not exist "models\scrfd_10g.onnx" set NEED_MODELS=1
if "%NEED_MODELS%"=="1" (
  echo The face models are not in the models folder yet.
  echo Downloading them now, about 190 MB. This needs internet this one time only.
  python scripts\download_models.py
  if errorlevel 1 (
    echo.
    echo The models could not be downloaded. Connect to the internet and double-click this file again.
    echo Or copy the two .onnx files into the models folder by hand. See README.md, step 4.
    pause
    exit /b 1
  )
)

rem open the browser after 4 seconds (gives the server time to start)
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
echo Starting... keep this window open while you use the app. Close it to stop the app.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
