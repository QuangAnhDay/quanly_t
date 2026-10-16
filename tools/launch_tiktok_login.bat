@echo off
chcp 65001 > nul
set ACC_NAME=%~1
if "%ACC_NAME%"=="" set ACC_NAME=kenh_le

title DANG NHAP TIKTOK - %ACC_NAME%
color 0a

if exist "E:\myProject\quanly_tt\.venv\Scripts\python.exe" (
    E:\myProject\quanly_tt\.venv\Scripts\python.exe tools\tiktok_login_helper.py %ACC_NAME%
) else (
    python tools\tiktok_login_helper.py %ACC_NAME%
)
