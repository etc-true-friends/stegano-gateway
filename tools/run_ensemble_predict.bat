@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set /p IMG=Image path: 
if "%IMG%"=="" exit /b 0
cd /d "%ROOT%\1_AI_Engine"
"%PY%" ensemble_predict.py --image "%IMG%" --models_dir "%ROOT%\1_AI_Engine\checkpoints"
exit /b %errorlevel%
