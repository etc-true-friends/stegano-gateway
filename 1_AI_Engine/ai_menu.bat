@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "AI_DIR=%~dp0"
for %%I in ("%AI_DIR%..") do set "ROOT=%%~fI"
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

rem Do not write %ROOT%\4_Local_Workspace directly here.
rem Some editors/scripts can corrupt \4 or \t into control characters.
set "WORKSPACE_NAME=4_Local_Workspace"
set "WS=%ROOT%\%WORKSPACE_NAME%"

cd /d "%AI_DIR%"

:main
cls
echo AI Engine Menu
echo Root: %ROOT%
echo Python: %PY%
echo Workspace: %WS%
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
set "SEL="
set /p "SEL=Select: "

if "%SEL%"=="12" exit /b 0
if "%SEL%"=="9" call :ensemble_predict & goto wait_main
if "%SEL%"=="10" call :ensemble_batch & goto wait_main
if "%SEL%"=="11" "%PY%" export_best_models.py --all & goto wait_main

call :set_dataset "%SEL%"
if errorlevel 1 goto main

goto action

:action
cls
echo Selected: !LABEL!
echo Dataset: !DATASET_DIR!
echo Checkpoints: !CHECKPOINTS_DIR!
echo Input mode: !INPUT_MODE!
echo Best metric: !BEST_METRIC!
echo.
echo 1. new training
echo 2. resume training
echo 3. val batch test
echo 4. single image test
echo 5. export best model to 1_AI_Engine\checkpoints
echo 6. back
echo.
set "ACT="
set /p "ACT=Action: "

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
set "INPUT_MODE=rgb"
set "BEST_METRIC=loss"
set "DEFAULT_LR=0.001"
set "DEFAULT_BATCH=16"
if "%~1"=="0" set "KEY=dataset"&set "LABEL=original"&set "CK=checkpoints"
if "%~1"=="1" set "KEY=dataset_dct_mid"&set "LABEL=dct_mid"&set "CK=checkpoints_dct_mid"
if "%~1"=="2" set "KEY=dataset_dwt_haar"&set "LABEL=dwt_haar"&set "CK=checkpoints_dwt_haar"
if "%~1"=="3" set "KEY=dataset_aes_random_lsb"&set "LABEL=aes_random_lsb"&set "CK=checkpoints_aes_random_lsb"
if "%~1"=="4" set "KEY=dataset_channel_lsb"&set "LABEL=channel_lsb"&set "CK=checkpoints_channel_lsb"
if "%~1"=="5" set "KEY=dataset_alpha_lsb"&set "LABEL=alpha_lsb"&set "CK=checkpoints_alpha_lsb"
if "%~1"=="6" set "KEY=dataset_edge_adaptive_lsb"&set "LABEL=edge_adaptive_lsb"&set "CK=checkpoints_edge_adaptive_lsb"&set "INPUT_MODE=lsb"&set "BEST_METRIC=balanced"&set "DEFAULT_LR=0.00015"&set "DEFAULT_BATCH=32"
if "%~1"=="7" set "KEY=dataset_texture_adaptive_lsb"&set "LABEL=texture_adaptive_lsb"&set "CK=checkpoints_texture_adaptive_lsb"&set "INPUT_MODE=lsb"&set "BEST_METRIC=balanced"&set "DEFAULT_BATCH=16"&set "DEFAULT_LR=0.00015"&set "WEIGHT_DECAY=0.0002"&set "NUM_WORKERS=2"&set "PREFETCH_FACTOR=2"
if "%~1"=="8" set "KEY=dataset_watermark"&set "LABEL=watermark"&set "CK=checkpoints_watermark"
if "%KEY%"=="" exit /b 1
set "DATASET_DIR=%WS%\%KEY%"
set "CHECKPOINTS_DIR=%WS%\%CK%"
exit /b 0

:read_params
if not exist "!DATASET_DIR!\train\cover" echo Missing folder: !DATASET_DIR!\train\cover&exit /b 1
if not exist "!DATASET_DIR!\train\stego" echo Missing folder: !DATASET_DIR!\train\stego&exit /b 1
if not exist "!DATASET_DIR!\val\cover" echo Missing folder: !DATASET_DIR!\val\cover&exit /b 1
if not exist "!DATASET_DIR!\val\stego" echo Missing folder: !DATASET_DIR!\val\stego&exit /b 1
set "TRAIN_COUNT="
set /p "TRAIN_COUNT=Train size Enter=182808: "
if "!TRAIN_COUNT!"=="" set "TRAIN_COUNT=182808"
set "VAL_COUNT="
set /p "VAL_COUNT=Val size Enter=45703: "
if "!VAL_COUNT!"=="" set "VAL_COUNT=45703"
set "EPOCHS="
set /p "EPOCHS=Epochs Enter=30: "
if "!EPOCHS!"=="" set "EPOCHS=30"
set "BATCH="
set /p "BATCH=Batch size Enter=!DEFAULT_BATCH!: "
if "!BATCH!"=="" set "BATCH=!DEFAULT_BATCH!"
set "LR="
set /p "LR=Learning rate Enter=!DEFAULT_LR!: "
if "!LR!"=="" set "LR=!DEFAULT_LR!"
exit /b 0

:train_new
echo.
echo [RUN] new training
call :read_params
if errorlevel 1 exit /b 1
if exist "!CHECKPOINTS_DIR!" rmdir /s /q "!CHECKPOINTS_DIR!"
mkdir "!CHECKPOINTS_DIR!" 2>nul
call :run_train
exit /b %errorlevel%

:train_resume
echo.
echo [RUN] resume training
call :read_params
if errorlevel 1 exit /b 1
mkdir "!CHECKPOINTS_DIR!" 2>nul
call :run_train
exit /b %errorlevel%

:run_train
set "SRNET_DATASET_DIR=!DATASET_DIR!"
set "SRNET_CHECKPOINTS_DIR=!CHECKPOINTS_DIR!"
set "SRNET_INPUT_MODE=!INPUT_MODE!"
set "SRNET_BEST_METRIC=!BEST_METRIC!"
if defined WEIGHT_DECAY (set "SRNET_WEIGHT_DECAY=!WEIGHT_DECAY!") else (if "!LABEL!"=="edge_adaptive_lsb" (set "SRNET_WEIGHT_DECAY=0.0005") else (set "SRNET_WEIGHT_DECAY=0.0002"))
if defined NUM_WORKERS (set "SRNET_NUM_WORKERS=!NUM_WORKERS!") else (set "SRNET_NUM_WORKERS=8")
if defined PREFETCH_FACTOR (set "SRNET_PREFETCH_FACTOR=!PREFETCH_FACTOR!") else (set "SRNET_PREFETCH_FACTOR=2")
echo [RUN] SRNET_DATASET_DIR=!SRNET_DATASET_DIR!
echo [RUN] SRNET_CHECKPOINTS_DIR=!SRNET_CHECKPOINTS_DIR!
echo [RUN] SRNET_INPUT_MODE=!SRNET_INPUT_MODE!
echo [RUN] SRNET_BEST_METRIC=!SRNET_BEST_METRIC!
echo [RUN] SRNET_WEIGHT_DECAY=!SRNET_WEIGHT_DECAY!
echo [RUN] SRNET_NUM_WORKERS=!SRNET_NUM_WORKERS!
echo [RUN] SRNET_PREFETCH_FACTOR=!SRNET_PREFETCH_FACTOR!
"%PY%" train.py --cover_path "!DATASET_DIR!\train\cover" --stego_path "!DATASET_DIR!\train\stego" --valid_cover_path "!DATASET_DIR!\val\cover" --valid_stego_path "!DATASET_DIR!\val\stego" --checkpoints_dir "!CHECKPOINTS_DIR!" --batch_size !BATCH! --num_epochs !EPOCHS! --train_size !TRAIN_COUNT! --val_size !VAL_COUNT! --lr !LR! --input_mode !INPUT_MODE! --best_metric !BEST_METRIC! --weight_decay !SRNET_WEIGHT_DECAY! --num_workers !SRNET_NUM_WORKERS! --prefetch_factor !SRNET_PREFETCH_FACTOR!
exit /b %errorlevel%

:batch_test
set "MODEL=!CHECKPOINTS_DIR!\best_srnet_model.pt"
if not exist "!MODEL!" echo Missing model: !MODEL!&exit /b 1
"%PY%" batch_test.py --cover_glob "!DATASET_DIR!\val\cover\*.png" --stego_glob "!DATASET_DIR!\val\stego\*.png" --checkpoint_path "!MODEL!" --batch_size 40 --input_mode !INPUT_MODE!
exit /b %errorlevel%

:single_test
set "MODEL=!CHECKPOINTS_DIR!\best_srnet_model.pt"
if not exist "!MODEL!" echo Missing model: !MODEL!&exit /b 1
set "IMG="
set /p "IMG=Image path: "
if "!IMG!"=="" exit /b 0
"%PY%" inference_test.py --checkpoint_path "!MODEL!" --img_dir "" --images "!IMG!" --input_mode !INPUT_MODE!
exit /b %errorlevel%

:ensemble_predict
set "IMG="
set /p "IMG=Image path: "
if "%IMG%"=="" exit /b 0
"%PY%" ensemble_predict.py --image "%IMG%" --models_dir "%AI_DIR%checkpoints"
exit /b %errorlevel%

:ensemble_batch
set "DATASET="
set /p "DATASET=Dataset folder Enter=dataset: "
if "%DATASET%"=="" set "DATASET=dataset"
"%PY%" ensemble_batch_test.py --cover_dir "%WS%\%DATASET%\val\cover" --stego_dir "%WS%\%DATASET%\val\stego" --models_dir "%AI_DIR%checkpoints" --output_csv "%WS%\ensemble_reports\%DATASET%_ensemble_report.csv"
exit /b %errorlevel%
