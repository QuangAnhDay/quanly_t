@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Chuyen thu muc lam viec ve dung thu muc chua file .bat nay
cd /d "%~dp0"

title XUONG SAN XUAT VIDEO TRUYEN - AUTOMATION SYSTEM
color 0b

echo ======================================================================
echo    HE THONG QUAN LY VA TU DONG HOA SAN XUAT VIDEO TRUYEN
echo ======================================================================
echo.
echo [1/2] Dang kiem tra moi truong Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ======================================================================
    echo [LOI] Khong tim thay Python tren he thong!
    echo Vui long cai dat Python va tich chon "Add Python to PATH".
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

echo [2/3] Dang kiem tra & khoi dong VoiceStudio API Server (Port 3900)...
if exist ".venv\Scripts\python.exe" (
    start /b .venv\Scripts\python.exe -c "import voicestudio_service; voicestudio_service.ensure_voicestudio_running()" > nul 2>&1
)

echo [3/3] Dang khoi dong Web Dashboard & Tu dong mo Trinh duyet...
echo.
echo ======================================================================
echo   HE THONG DANG HOAT DONG!
echo   - Web Dashboard : http://localhost:8888 (Tu dong mo Trinh duyet)
echo   - VoiceStudio API: http://127.0.0.1:3900 (Chay ngam)
echo   - Nhan Ctrl+C tai cua so nay de dung he thong khi xong viec.
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -X utf8 server.py
) else (
    python -X utf8 server.py
)

if %errorlevel% neq 0 (
    echo.
    echo ======================================================================
    echo [THONG BAO] Server da dung hoac gap su co.
    echo ======================================================================
    pause
)
