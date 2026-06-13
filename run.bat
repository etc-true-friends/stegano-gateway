@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"

:main
cls
echo Stegano Gateway Menu
echo Root: %ROOT%
echo.
echo 1. install / update environment
echo 2. AI training / single model menu
echo 3. workspace / dataset menu
echo 4. ensemble single image predict
echo 5. ensemble validation test
echo 6. check environment
echo 7. create workspace folders
echo 8. cleanup old root batch files
echo 9. exit
echo.
set /p SEL=Select: 
if "%SEL%"=="1" call "%ROOT%install.bat" & goto wait
if "%SEL%"=="2" call "%ROOT%1_AI_Engine\ai_menu.bat" & goto main
if "%SEL%"=="3" call "%ROOT%4_Local_Workspace\workspace_menu.bat" & goto main
if "%SEL%"=="4" call "%ROOT%tools\run_ensemble_predict.bat" & goto wait
if "%SEL%"=="5" call "%ROOT%tools\run_ensemble_batch_test.bat" & goto wait
if "%SEL%"=="6" call "%ROOT%tools\check_environment.bat" & goto wait
if "%SEL%"=="7" call "%ROOT%tools\setup_workspace.bat" & goto wait
if "%SEL%"=="8" call "%ROOT%tools\cleanup_old_batch_files.bat" & goto wait
if "%SEL%"=="9" exit /b 0
goto main

:wait
echo.
pause
goto main
