@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Cheonsang RPG - Run
set "LOG=%~dp0RUN_LOG.txt"
>"%LOG%" echo [Cheonsang RPG - Run Log]
>>"%LOG%" echo Folder: %CD%
if not exist "%~dp0game.py" (>>"%LOG%" echo ERROR: game.py is missing. & goto :fail)
call :find_python
if not defined PY_CMD (>>"%LOG%" echo ERROR: Python 3.10+ not found. & goto :fail)
echo [1/3] Python: %PY_CMD%
%PY_CMD% --version >>"%LOG%" 2>&1
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo [2/3] Creating a private Python environment...
  %PY_CMD% -m venv "%~dp0.venv" >>"%LOG%" 2>&1
  if errorlevel 1 goto :fail
)
set "VPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VPY%" (>>"%LOG%" echo ERROR: venv python not found. & goto :fail)
"%VPY%" -m pip install --disable-pip-version-check pygame-ce==2.5.8 >>"%LOG%" 2>&1
if errorlevel 1 goto :fail
echo [3/3] Starting Cheonsang RPG...
"%VPY%" "%~dp0game.py" >>"%LOG%" 2>&1
if errorlevel 1 goto :fail
echo Game closed normally.
pause
exit /b 0
:find_python
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.14 --version >nul 2>&1
  if not errorlevel 1 set "PY_CMD=py -3.14"
)
if not defined PY_CMD (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
      py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
      if not errorlevel 1 set "PY_CMD=py -3"
    )
  )
)
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
  )
)
exit /b 0
:fail
echo.
echo [FAILED] See RUN_LOG.txt for the error details.
if exist "%LOG%" type "%LOG%"
pause
exit /b 1
