@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
cd /d "%ROOT%"
call "%ROOT%tools\setup_workspace.bat"
if errorlevel 1 exit /b 1
call "%ROOT%1_AI_Engine\install.bat"
exit /b %errorlevel%
