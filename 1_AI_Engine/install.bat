@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "AI_DIR=%~dp0"
for %%I in ("%AI_DIR%..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\.venv"
set "PY=%VENV%\Scripts\python.exe"
cd /d "%ROOT%"

if not exist "%PY%" (
  python -m venv "%VENV%"
  if errorlevel 1 (
    echo venv creation failed. Install Python 3.10 or 3.11 and add it to PATH.
    pause
    exit /b 1
  )
)

"%PY%" -m pip install --upgrade pip --no-warn-script-location
if errorlevel 1 exit /b 1
"%PY%" -m pip install -r "%ROOT%\requirements.txt" --no-warn-script-location
if errorlevel 1 exit /b 1

where nvidia-smi >nul 2>nul
if not errorlevel 1 (
  "%PY%" -m pip uninstall -y torch torchvision torchaudio
  "%PY%" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --no-warn-script-location
)

"%PY%" "%ROOT%\scripts\check_environment.py"
exit /b %errorlevel%
