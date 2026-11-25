@echo off
rem Activates the virtual environment, gets the face models if they are missing,
rem starts the server and opens the browser. Double-click this file.
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo The app is not installed yet. Double-click demo.bat once, or follow "Install" in README.md.
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
    echo Or copy the two .onnx files into the models folder by hand. See "Install" in README.md.
    pause
    exit /b 1
  )
)

rem picks a free port (8000 first), starts the server and opens the browser once it answers
python scripts\launch.py
pause
