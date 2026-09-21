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

echo [2/2] Dang khoi dong He thong va Web Dashboard...
echo.
echo ======================================================================
echo   HE THONG DANG HOAT DONG!
echo   - Web Dashboard: http://localhost:8888 (Trinh duyet se tu dong mo)
echo   - Nhap du lieu kịch ban va tao video thoai mai
echo   - Nhan Ctrl+C tai cua so nay de dung he thong khi xong viec.
echo ======================================================================
echo.

python -X utf8 server.py

if %errorlevel% neq 0 (
    echo.
    echo ======================================================================
    echo [THONG BAO] Server da dung hoac gap su co.
    echo ======================================================================
    pause
)
