@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
set "OUT=%~dp0PC_ENVIRONMENT.txt"
>"%OUT%" echo [Cheonsang RPG - PC Environment]
>>"%OUT%" echo Date: %date% %time%
>>"%OUT%" echo Folder: %CD%
>>"%OUT%" echo.
>>"%OUT%" echo ==== Windows ====
ver >>"%OUT%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ==== Python Launcher ====
where py >>"%OUT%" 2>&1
py -0p >>"%OUT%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ==== Python 3.14 ====
py -3.14 --version >>"%OUT%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ==== python command ====
where python >>"%OUT%" 2>&1
python --version >>"%OUT%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ==== Project files ====
dir /b >>"%OUT%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ==== Private environment ====
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version >>"%OUT%" 2>&1
  ".venv\Scripts\python.exe" -m pip show pygame-ce >>"%OUT%" 2>&1
  ".venv\Scripts\python.exe" -m pip show pyinstaller >>"%OUT%" 2>&1
) else (
  >>"%OUT%" echo .venv is not created yet.
)
echo PC check complete: PC_ENVIRONMENT.txt
echo Please attach that file in the chat.
pause
