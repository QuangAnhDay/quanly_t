@echo off
chcp 65001 > nul
echo ========================================================
echo   KHỞI CHẠY 5 PROFILE CHROME ĐĂNG NHẬP SẴN TÀI KHOẢN CLAUDE
echo ========================================================

set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist %CHROME_PATH% (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
if not exist %CHROME_PATH% (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

echo [1/5] Đang mở Profile 7 (quanganhfamily08@gmail.com - Anh Le)...
start "" %CHROME_PATH% --profile-directory="Profile 7" "https://claude.ai"
timeout /t 1 /nobreak > nul

echo [2/5] Đang mở Profile 2 (quanganh.bn0805@gmail.com - Quang Anh Le)...
start "" %CHROME_PATH% --profile-directory="Profile 2" "https://claude.ai"
timeout /t 1 /nobreak > nul

echo [3/5] Đang mở Profile 4 (quanganh08.bn@gmail.com - Quang Anh Le)...
start "" %CHROME_PATH% --profile-directory="Profile 4" "https://claude.ai"
timeout /t 1 /nobreak > nul

echo [4/5] Đang mở Profile 5 (quanganhdaymmo@gmail.com - Quang Anh Le)...
start "" %CHROME_PATH% --profile-directory="Profile 5" "https://claude.ai"
timeout /t 1 /nobreak > nul

echo [5/5] Đang mở Profile 1 (24100414@st.phenikaa-uni.edu.vn - Phenikaa)...
start "" %CHROME_PATH% --profile-directory="Profile 1" "https://claude.ai"

echo ========================================================
echo   ĐÃ MỞ THÀNH CÔNG 5 TÀI KHOẢN CLAUDE CHÍNH XÁC!
echo ========================================================
