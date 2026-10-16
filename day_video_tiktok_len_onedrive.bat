@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

title DONG BO VIDEO TIKTOK SANG ONEDRIVE
color 0a

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
)

%PYTHON_CMD% sync_tiktok_to_onedrive.py

echo.
pause
