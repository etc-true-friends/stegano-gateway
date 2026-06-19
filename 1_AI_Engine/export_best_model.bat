@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "AI_DIR=%~dp0"
for %%I in ("%AI_DIR%..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set /p METHOD=Method name: 
if "%METHOD%"=="" exit /b 0
cd /d "%AI_DIR%"
"%PY%" export_best_models.py --method "%METHOD%"
exit /b %errorlevel%
