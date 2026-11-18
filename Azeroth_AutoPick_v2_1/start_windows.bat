@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Azeroth AutoPick - The Build Forge

set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=py -3.12"
  if not defined PY (
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=py -3.11"
  )
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
  )
)
if not defined PY (
  echo Python 3.11 or 3.12 is required.
  echo Install Python for Windows from https://www.python.org/downloads/windows/
  echo During installation, tick "Add python.exe to PATH".
  echo Restart this launcher afterwards.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [Build Forge] Creating local Python environment...
  %PY% -m venv .venv
  if errorlevel 1 (echo Virtual environment setup failed.& pause & exit /b 1)
)
if not exist ".venv\.buildforge_ready_v2" (
  echo [Build Forge] First run: installing local OCR and screen tools...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 (echo Pip update failed.& pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Dependency installation failed. Check internet access.& pause & exit /b 1)
  echo ready>".venv\.buildforge_ready_v2"
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 (echo Build Forge stopped unexpectedly. See any error above.& pause & exit /b 1)
endlocal
