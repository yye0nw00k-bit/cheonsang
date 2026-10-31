@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Cheonsang RPG - Build EXE
set "LOG=%~dp0BUILD_LOG.txt"
>"%LOG%" echo [Cheonsang RPG - EXE Build Log]
>>"%LOG%" echo Folder: %CD%
if not exist "%~dp0game.py" (>>"%LOG%" echo ERROR: game.py is missing. & goto :fail)
call :find_python
if not defined PY_CMD (>>"%LOG%" echo ERROR: Python 3.10+ not found. & goto :fail)
echo Python: %PY_CMD%
%PY_CMD% --version >>"%LOG%" 2>&1
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo [1/4] Creating a private Python environment...
  %PY_CMD% -m venv "%~dp0.venv" >>"%LOG%" 2>&1
  if errorlevel 1 goto :fail
)
set "VPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VPY%" (>>"%LOG%" echo ERROR: venv python not found. & goto :fail)
echo [2/4] Updating pip...
"%VPY%" -m pip install --upgrade pip >>"%LOG%" 2>&1
if errorlevel 1 goto :fail
echo [3/4] Installing game and EXE build packages...
"%VPY%" -m pip install pygame-ce==2.5.8 pyinstaller==6.22.3 >>"%LOG%" 2>&1
if errorlevel 1 goto :fail
echo [4/4] Building one EXE...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name CheonsangRPG --collect-all pygame --distpath "%~dp0dist" --workpath "%~dp0build" "%~dp0game.py" >>"%LOG%" 2>&1
if errorlevel 1 goto :fail
if not exist "%~dp0dist\CheonsangRPG.exe" (>>"%LOG%" echo ERROR: EXE not created. & goto :fail)
copy /y "%~dp0server_config.json" "%~dp0dist\server_config.json" >>"%LOG%" 2>&1
echo.
echo BUILD SUCCESS!
echo EXE: dist\CheonsangRPG.exe
echo Keep server_config.json beside the EXE for online play.
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
echo [FAILED] See BUILD_LOG.txt for the error details.
if exist "%LOG%" type "%LOG%"
pause
exit /b 1
