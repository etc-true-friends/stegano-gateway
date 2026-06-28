@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set /p DATASET=Dataset folder name Enter=dataset: 
if "%DATASET%"=="" set "DATASET=dataset"
cd /d "%ROOT%\1_AI_Engine"
"%PY%" ensemble_batch_test.py --cover_dir "%ROOT%\4_Local_Workspace\%DATASET%\val\cover" --stego_dir "%ROOT%\4_Local_Workspace\%DATASET%\val\stego" --models_dir "%ROOT%\1_AI_Engine\checkpoints" --output_csv "%ROOT%\4_Local_Workspace\ensemble_reports\%DATASET%_ensemble_report.csv"
exit /b %errorlevel%
