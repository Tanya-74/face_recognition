@echo off
rem One double-click demo: creates the virtual environment the first time, installs the
rem packages and models, starts the app and runs it on the sample photos in your browser.
cd /d "%~dp0"
set PYTHONUTF8=1

set "PY="
py -3.11 -c "pass" >nul 2>&1 && set "PY=py -3.11"
if not defined PY python -c "import sys; sys.exit(sys.version_info[:2] != (3, 11))" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3.11 was not found on this computer.
  echo Install it with:   winget install Python.Python.3.11
  echo or download it from https://www.python.org/downloads/release/python-3119/
  echo and tick "Add python.exe to PATH". Then double-click this file again.
  pause
  exit /b 1
)

%PY% scripts\demo.py
pause
