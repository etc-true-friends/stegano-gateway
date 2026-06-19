@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul

set "WS=%~dp0"
if "%WS:~-1%"=="\" set "WS=%WS:~0,-1%"
for %%I in ("%WS%\..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

:main
cls
echo Workspace / Dataset Menu
echo Workspace: %WS%
echo Root: %ROOT%
echo Python: %PY%
echo.
echo 1. create workspace folders
echo 2. prepare base cover dataset from real_images
echo 3. build dct_mid dataset
echo 4. build dwt_haar dataset
echo 5. build aes_random_lsb dataset
echo 6. build channel_lsb dataset
echo 7. build alpha_lsb dataset
echo 8. build edge_adaptive_lsb dataset
echo 9. build texture_adaptive_lsb dataset
echo W. build watermark dataset
echo A. build all stego datasets
echo B. back
echo.
choice /C 123456789WAB /N /M "Select: "
set "SEL=%ERRORLEVEL%"

if "%SEL%"=="1" goto create_workspace
if "%SEL%"=="2" goto prepare_base
if "%SEL%"=="3" goto dct_mid
if "%SEL%"=="4" goto dwt_haar
if "%SEL%"=="5" goto aes_random_lsb
if "%SEL%"=="6" goto channel_lsb
if "%SEL%"=="7" goto alpha_lsb
if "%SEL%"=="8" goto edge_adaptive_lsb
if "%SEL%"=="9" goto texture_adaptive_lsb
if "%SEL%"=="10" goto watermark
if "%SEL%"=="11" goto all
if "%SEL%"=="12" exit /b 0
goto main

:create_workspace
call "%ROOT%\tools\setup_workspace.bat"
goto wait

:prepare_base
echo.
echo [INFO] Put source images here first:
echo %WS%\real_images
echo.
echo [RUN] prepare base cover dataset
echo [RUN] python=%PY%
echo.
"%PY%" "%ROOT%\scripts\prepare_base_dataset.py" --workspace "%WS%"
goto wait

:dct_mid
set "STEGANO_VARIANT=dct_mid"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_dct_mid_stego.py"
goto run_one

:dwt_haar
set "STEGANO_VARIANT=dwt_haar"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_dwt_haar_stego.py"
goto run_one

:aes_random_lsb
set "STEGANO_VARIANT=aes_random_lsb"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_aes_random_lsb_stego.py"
goto run_one

:channel_lsb
set "STEGANO_VARIANT=channel_lsb"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_channel_lsb_stego.py"
goto run_one

:alpha_lsb
set "STEGANO_VARIANT=alpha_lsb"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_alpha_lsb_stego.py"
goto run_one

:edge_adaptive_lsb
set "STEGANO_VARIANT=edge_adaptive_lsb"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_edge_adaptive_lsb_stego.py"
goto run_one

:texture_adaptive_lsb
set "STEGANO_VARIANT=texture_adaptive_lsb"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_texture_adaptive_lsb_stego.py"
goto run_one

:watermark
set "STEGANO_VARIANT=watermark"
set "STEGANO_SCRIPT=%ROOT%\scripts\build_watermark_stego.py"
goto run_one

:run_one
echo.
echo [RUN] variant=%STEGANO_VARIANT%
echo [RUN] script=%STEGANO_SCRIPT%
echo [RUN] python=%PY%
echo.
"%PY%" "%ROOT%\scripts\make_dataset_variant.py" --workspace "%WS%" --variant "%STEGANO_VARIANT%" --script "%STEGANO_SCRIPT%"
goto wait

:all
call :run_all dct_mid build_dct_mid_stego.py
if errorlevel 1 goto wait
call :run_all dwt_haar build_dwt_haar_stego.py
if errorlevel 1 goto wait
call :run_all aes_random_lsb build_aes_random_lsb_stego.py
if errorlevel 1 goto wait
call :run_all channel_lsb build_channel_lsb_stego.py
if errorlevel 1 goto wait
call :run_all alpha_lsb build_alpha_lsb_stego.py
if errorlevel 1 goto wait
call :run_all edge_adaptive_lsb build_edge_adaptive_lsb_stego.py
if errorlevel 1 goto wait
call :run_all texture_adaptive_lsb build_texture_adaptive_lsb_stego.py
if errorlevel 1 goto wait
call :run_all watermark build_watermark_stego.py
goto wait

:run_all
set "STEGANO_VARIANT=%~1"
set "STEGANO_SCRIPT=%ROOT%\scripts\%~2"
echo.
echo [RUN] variant=%STEGANO_VARIANT%
echo [RUN] script=%STEGANO_SCRIPT%
echo [RUN] python=%PY%
echo.
"%PY%" "%ROOT%\scripts\make_dataset_variant.py" --workspace "%WS%" --variant "%STEGANO_VARIANT%" --script "%STEGANO_SCRIPT%" --yes yes
exit /b %ERRORLEVEL%

:wait
echo.
pause
goto main
