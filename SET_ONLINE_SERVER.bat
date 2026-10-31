@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.14 "%~dp0SET_ONLINE_SERVER.py"
  if not errorlevel 1 exit /b 0
  py -3 "%~dp0SET_ONLINE_SERVER.py"
  if not errorlevel 1 exit /b 0
)
python "%~dp0SET_ONLINE_SERVER.py"
if errorlevel 1 pause
