@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.14 "%~dp0IMPORT_LOCAL_ACCOUNTS.py"
  if not errorlevel 1 goto :done
  py -3 "%~dp0IMPORT_LOCAL_ACCOUNTS.py"
  goto :done
)
python "%~dp0IMPORT_LOCAL_ACCOUNTS.py"
:done
pause
