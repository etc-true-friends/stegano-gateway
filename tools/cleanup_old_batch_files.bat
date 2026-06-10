@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT=%%~fI"

del "%ROOT%\run_ai_menu.bat" 2>nul
del "%ROOT%\run_dataset_menu.bat" 2>nul
del "%ROOT%\run_ensemble_predict.bat" 2>nul
del "%ROOT%\run_ensemble_batch_test.bat" 2>nul
del "%ROOT%\setup_workspace.bat" 2>nul
del "%ROOT%\check_environment.bat" 2>nul

del "%ROOT%\4_Local_Workspace\build_stego_dataset_menu.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_all_stego_datasets.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_dct_mid_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_dwt_haar_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_aes_random_lsb_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_channel_lsb_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_alpha_lsb_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_edge_adaptive_lsb_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_texture_adaptive_lsb_dataset.bat" 2>nul
del "%ROOT%\4_Local_Workspace\build_watermark_dataset.bat" 2>nul

echo Old root and workspace batch files cleaned.
exit /b 0
