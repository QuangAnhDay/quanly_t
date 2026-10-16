# -*- coding: utf-8 -*-
"""
Helper script to launch interactive TikTok login with Google Chrome and clear CLI feedback.
"""
import sys
import os
import re
import time
import subprocess

# Set encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def sanitize_account_name(name: str) -> str:
    name = name.strip().lower()
    # Replace Vietnamese accents if any
    replacements = {
        'à':'a', 'á':'a', 'ả':'a', 'ã':'a', 'ạ':'a', 'ă':'a', 'ằ':'a', 'ắ':'a', 'ẳ':'a', 'ẵ':'a', 'ặ':'a',
        'â':'a', 'ầ':'a', 'ấ':'a', 'ẩ':'a', 'ẫ':'a', 'ậ':'a',
        'è':'e', 'é':'e', 'ẻ':'e', 'ẽ':'e', 'ẹ':'e', 'ê':'e', 'ề':'e', 'ế':'e', 'ể':'e', 'ễ':'e', 'ệ':'e',
        'ì':'i', 'í':'i', 'ỉ':'i', 'ĩ':'i', 'ị':'i',
        'ò':'o', 'ó':'o', 'ỏ':'o', 'õ':'o', 'ọ':'o', 'ô':'o', 'ồ':'o', 'ố':'o', 'ổ':'o', 'ỗ':'o', 'ộ':'o',
        'ơ':'o', 'ờ':'o', 'ớ':'o', 'ở':'o', 'ỡ':'o', 'ợ':'o',
        'ù':'u', 'ú':'u', 'ủ':'u', 'ũ':'u', 'ụ':'u', 'ư':'u', 'ừ':'u', 'ứ':'u', 'ử':'u', 'ữ':'u', 'ự':'u',
        'ỳ':'y', 'ý':'y', 'ỷ':'y', 'ỹ':'y', 'ỵ':'y',
        'đ':'d'
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    name = re.sub(r'[^a-z0-9._-]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name or "account"

def main():
    if len(sys.argv) < 2:
        print("[LOI] Thieu ten tai khoan!")
        input("\nNhan Enter de thoat...")
        return

    raw_name = sys.argv[1]
    acc_name = sanitize_account_name(raw_name)

    print("=" * 65)
    print("   DANG NHAP TIKTOK QUA GOOGLE CHROME (CHI CAN DANG NHAP 1 LAN)")
    print("=" * 65)
    print(f"[*] Tai khoan muc tieu : {acc_name}")
    print("[*] Trinh duyet        : Google Chrome (Ho tro dang nhap Google)")
    print("[*] Trang dang nhap    : https://www.tiktok.com/login")
    print("-" * 65)
    print("[HUONG DAN]:")
    print(" 1. Cua so Google Chrome se duoc mo len trong vai giay toi.")
    print(" 2. Tren man hinh TikTok, ban co the chon:")
    print("    -> 'Tiep tuc voi Google' (Dang nhap bang tai khoan Google cua ban)")
    print("    -> Hoac Quet ma QR / So dien thoai / Mat khau.")
    print(" 3. Sau khi dang nhap thanh cong, he thong se TU DONG luu phien (Cookies)")
    print("    va dong trinh duyet. Ban se khong can dang nhap lai lan nao nua!")
    print("=" * 65)
    print()

    # Path to autotok python and script
    autotok_dir = r"D:\myProject\ATP_tiktok"
    autotok_py = os.path.join(autotok_dir, ".venv", "Scripts", "python.exe")
    autotok_cli = os.path.join(autotok_dir, "cli.py")

    if not os.path.exists(autotok_py):
        print(f"[LOI] Khong tim thay Python tai {autotok_py}")
        input("\nNhan Enter de thoat...")
        return

    # Ensure environment forces Chrome
    env = os.environ.copy()
    env["AUTOTOK_BROWSER_CHANNEL"] = "chrome"

    cmd = [
        autotok_py,
        autotok_cli,
        "login",
        "-n",
        acc_name
    ]

    print(f"[...] Dang khoi dong Google Chrome cho '{acc_name}'...")
    try:
        proc = subprocess.run(cmd, cwd=autotok_dir, env=env)
        if proc.returncode == 0:
            print()
            print("=" * 65)
            print(f"[THANH CONG] Da luu phien dang nhap thanh cong cho: {acc_name}!")
            print("Tu gio he thong se tu dong up video len kenh nay!")
            print("=" * 65)
            print()
            time.sleep(3)
        else:
            print()
            print(f"[THONG BAO] Tien trinh ket thuc voi ma loi: {proc.returncode}")
            input("\nNhan Enter de dong cua so...")
    except Exception as e:
        print(f"[LOI NGOAI LE]: {e}")
        input("\nNhan Enter de dong cua so...")

if __name__ == "__main__":
    main()
