@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "AI_DIR=%~dp0"
for %%I in ("%AI_DIR%..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "WS=%ROOT%\4_Local_Workspace"
cd /d "%AI_DIR%"

:main
cls
echo AI Engine Menu
echo Root: %ROOT%
echo Python: %PY%
echo.
echo 0. original
echo 1. dct_mid
echo 2. dwt_haar
echo 3. aes_random_lsb
echo 4. channel_lsb
echo 5. alpha_lsb
echo 6. edge_adaptive_lsb
echo 7. texture_adaptive_lsb
echo 8. watermark
echo 9. ensemble predict
echo 10. ensemble val test
echo 11. export all best models
echo 12. exit
echo.
set /p SEL=Select: 
if "%SEL%"=="12" exit /b 0
if "%SEL%"=="9" call :ensemble_predict & goto wait_main
if "%SEL%"=="10" call :ensemble_batch & goto wait_main
if "%SEL%"=="11" "%PY%" export_best_models.py --all & goto wait_main
call :set_dataset "%SEL%"
if errorlevel 1 goto main

:action
cls
echo Selected: !LABEL!
echo Dataset: !DATASET_DIR!
echo Checkpoints: !CHECKPOINTS_DIR!
echo.
echo 1. new training
echo 2. resume training
echo 3. val batch test
echo 4. single image test
echo 5. export best model to 4_Local_Workspace\models
echo 6. back
echo.
set /p ACT=Action: 
if "%ACT%"=="6" goto main
if "%ACT%"=="1" call :train_new & goto wait_action
if "%ACT%"=="2" call :train_resume & goto wait_action
if "%ACT%"=="3" call :batch_test & goto wait_action
if "%ACT%"=="4" call :single_test & goto wait_action
if "%ACT%"=="5" "%PY%" export_best_models.py --method "!LABEL!" & goto wait_action
goto action

:wait_action
echo.
pause
goto action

:wait_main
echo.
pause
goto main

:set_dataset
set "KEY="
set "LABEL="
set "CK="
if "%~1"=="0" set "KEY=dataset"&set "LABEL=original"&set "CK=checkpoints"
if "%~1"=="1" set "KEY=dataset_dct_mid"&set "LABEL=dct_mid"&set "CK=checkpoints_dct_mid"
if "%~1"=="2" set "KEY=dataset_dwt_haar"&set "LABEL=dwt_haar"&set "CK=checkpoints_dwt_haar"
if "%~1"=="3" set "KEY=dataset_aes_random_lsb"&set "LABEL=aes_random_lsb"&set "CK=checkpoints_aes_random_lsb"
if "%~1"=="4" set "KEY=dataset_channel_lsb"&set "LABEL=channel_lsb"&set "CK=checkpoints_channel_lsb"
if "%~1"=="5" set "KEY=dataset_alpha_lsb"&set "LABEL=alpha_lsb"&set "CK=checkpoints_alpha_lsb"
if "%~1"=="6" set "KEY=dataset_edge_adaptive_lsb"&set "LABEL=edge_adaptive_lsb"&set "CK=checkpoints_edge_adaptive_lsb"
if "%~1"=="7" set "KEY=dataset_texture_adaptive_lsb"&set "LABEL=texture_adaptive_lsb"&set "CK=checkpoints_texture_adaptive_lsb"
if "%~1"=="8" set "KEY=dataset_watermark"&set "LABEL=watermark"&set "CK=checkpoints_watermark"
if "%KEY%"=="" exit /b 1
set "DATASET_DIR=%WS%\%KEY%"
set "CHECKPOINTS_DIR=%WS%\%CK%"
exit /b 0

:count_images
set "COUNT=%~1"
set "DIR=%~2"
for /f %%C in ('powershell -NoProfile -Command "if(Test-Path '%~2'){(Get-ChildItem -Path '%~2' -File -Include *.png,*.jpg,*.jpeg,*.bmp,*.webp -Recurse).Count}else{0}"') do set "%~1=%%C"
exit /b 0

:read_params
call :count_images TRAIN_COUNT "!DATASET_DIR!\train\cover"
call :count_images VAL_COUNT "!DATASET_DIR!\val\cover"
if "!TRAIN_COUNT!"=="0" echo No train cover images found.&exit /b 1
if "!VAL_COUNT!"=="0" echo No val cover images found.&exit /b 1
set /p EPOCHS=Epochs Enter=30: 
if "!EPOCHS!"=="" set "EPOCHS=30"
set /p BATCH=Batch size Enter=16: 
if "!BATCH!"=="" set "BATCH=16"
set /p LR=Learning rate Enter=0.001: 
if "!LR!"=="" set "LR=0.001"
exit /b 0

:train_new
call :read_params
if errorlevel 1 exit /b 1
if exist "!CHECKPOINTS_DIR!" rmdir /s /q "!CHECKPOINTS_DIR!"
mkdir "!CHECKPOINTS_DIR!"
"%PY%" train.py --cover_path "!DATASET_DIR!\train\cover" --stego_path "!DATASET_DIR!\train\stego" --valid_cover_path "!DATASET_DIR!\val\cover" --valid_stego_path "!DATASET_DIR!\val\stego" --checkpoints_dir "!CHECKPOINTS_DIR!" --batch_size !BATCH! --num_epochs !EPOCHS! --train_size !TRAIN_COUNT! --val_size !VAL_COUNT! --lr !LR!
exit /b %errorlevel%

:train_resume
call :read_params
if errorlevel 1 exit /b 1
mkdir "!CHECKPOINTS_DIR!" 2>nul
"%PY%" train.py --cover_path "!DATASET_DIR!\train\cover" --stego_path "!DATASET_DIR!\train\stego" --valid_cover_path "!DATASET_DIR!\val\cover" --valid_stego_path "!DATASET_DIR!\val\stego" --checkpoints_dir "!CHECKPOINTS_DIR!" --batch_size !BATCH! --num_epochs !EPOCHS! --train_size !TRAIN_COUNT! --val_size !VAL_COUNT! --lr !LR!
exit /b %errorlevel%

:batch_test
set "MODEL=!CHECKPOINTS_DIR!\best_srnet_model.pt"
if not exist "!MODEL!" echo Missing model: !MODEL!&exit /b 1
"%PY%" batch_test.py --cover_glob "!DATASET_DIR!\val\cover\*.png" --stego_glob "!DATASET_DIR!\val\stego\*.png" --checkpoint_path "!MODEL!" --batch_size 40
exit /b %errorlevel%

:single_test
set "MODEL=!CHECKPOINTS_DIR!\best_srnet_model.pt"
if not exist "!MODEL!" echo Missing model: !MODEL!&exit /b 1
set /p IMG=Image path: 
if "!IMG!"=="" exit /b 0
"%PY%" inference_test.py --checkpoint_path "!MODEL!" --img_dir "" --images "!IMG!"
exit /b %errorlevel%

:ensemble_predict
set /p IMG=Image path: 
if "%IMG%"=="" exit /b 0
"%PY%" ensemble_predict.py --image "%IMG%" --models_dir "%WS%\models"
exit /b %errorlevel%

:ensemble_batch
set /p DATASET=Dataset folder Enter=dataset: 
if "%DATASET%"=="" set "DATASET=dataset"
"%PY%" ensemble_batch_test.py --cover_dir "%WS%\%DATASET%\val\cover" --stego_dir "%WS%\%DATASET%\val\stego" --models_dir "%WS%\models" --output_csv "%WS%\ensemble_reports\%DATASET%_ensemble_report.csv"
exit /b %errorlevel%
