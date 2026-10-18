# -*- coding: utf-8 -*-
"""
Công cụ tự động đồng bộ Video TikTok từ quanly_tt/outputs sang OneDrive.
- Tự động tìm tất cả file video định dạng TikTok (*_tiktok.mp4).
- Tự động bỏ qua file YouTube, file audio WAV, file thumbnail PNG.
- Tự động phân loại:
    + Tập lẻ (KB001, KB003, KB005...) -> OneDrive/TikTok_AutoPost/kenh_le/
    + Tập chẵn (KB002, KB004, KB006...) -> OneDrive/TikTok_AutoPost/kenh_chan/
    + Hoặc sao chép vào tong_hop/ nếu muốn
- Tự động bỏ qua các file đã được đẩy sang OneDrive trước đó.
"""
import os
import re
import sys
import shutil
from pathlib import Path

def get_onedrive_path():
    """Tự động phát hiện vị trí thư mục OneDrive trên máy tính"""
    try:
        import winreg
        for reg_path in [
            r"Software\Microsoft\OneDrive\Accounts\Personal",
            r"Software\Microsoft\OneDrive"
        ]:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    val, _ = winreg.QueryValueEx(key, "UserFolder")
                    if val and os.path.exists(val):
                        return val
            except Exception:
                pass
    except Exception:
        pass

    for var in ["OneDriveConsumer", "OneDrive", "OneDriveCommercial"]:
        p = os.environ.get(var)
        if p and os.path.exists(p):
            return p

    default_p = os.path.join(os.path.expanduser("~"), "OneDrive")
    if os.path.exists(default_p):
        return default_p
    return None

def sync_videos():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = os.path.join(base_dir, "outputs")

    if not os.path.exists(outputs_dir):
        print(f"[!] Không tìm thấy thư mục outputs tại: {outputs_dir}")
        return

    od_root = get_onedrive_path()
    if not od_root:
        print("[!] Không tìm thấy thư mục OneDrive trên máy tính của bạn!")
        return

    target_base = os.path.join(od_root, "TikTok_AutoPost")
    kenh_le_dir = os.path.join(target_base, "kenh_le")
    kenh_chan_dir = os.path.join(target_base, "kenh_chan")
    tong_hop_dir = os.path.join(target_base, "tong_hop")

    for d in [kenh_le_dir, kenh_chan_dir, tong_hop_dir]:
        os.makedirs(d, exist_ok=True)

    print("=" * 65)
    print("      DONG BO VIDEO TIKTOK SANG ONEDRIVE (TIET KIEM DUNG LUONG)")
    print("=" * 65)
    print(f"[*] Nguồn   : {outputs_dir}")
    print(f"[*] Đích    : {target_base}")
    print("-" * 65)

    copied_le = 0
    copied_chan = 0
    skipped = 0
    total_bytes = 0

    # Quét đệ quy tìm các file video TikTok
    for root, dirs, files in os.walk(outputs_dir):
        for f in sorted(files):
            # Chỉ lấy các file video có chứa 'tiktok' và đuôi .mp4
            if not f.lower().endswith((".mp4", ".mov")):
                continue
            if "tiktok" not in f.lower():
                continue

            src_file = os.path.join(root, f)
            file_size = os.path.getsize(src_file)

            # Nhận diện số tập từ tên file hoặc tên thư mục cha (vd: KB001)
            digits = re.findall(r'\d+', f)
            if not digits:
                # Thử tìm trong tên thư mục cha
                parent_name = os.path.basename(root)
                digits = re.findall(r'\d+', parent_name)

            is_even = False
            if digits:
                num = int(digits[-1])
                is_even = (num % 2 == 0)

            # Phân loại đích đến
            target_sub = kenh_chan_dir if is_even else kenh_le_dir
            dest_file = os.path.join(target_sub, f)

            # Kiểm tra xem file đã tồn tại bên đích (kể cả trong thư mục _posted) chưa
            posted_check = os.path.join(target_sub, "_posted", f)
            if os.path.exists(dest_file) or os.path.exists(posted_check):
                skipped += 1
                continue

            # Thực hiện copy sang OneDrive
            sub_name = "Kênh Chẵn" if is_even else "Kênh Lẻ"
            print(f"[+] Sao chép [{sub_name}]: {f} ({round(file_size / (1024*1024), 1)} MB)...")
            try:
                shutil.copy2(src_file, dest_file)
                total_bytes += file_size
                if is_even:
                    copied_chan += 1
                else:
                    copied_le += 1
            except Exception as e:
                print(f"[!] Lỗi sao chép {f}: {e}")

    print("-" * 65)
    print("KET QUA DONG BO:")
    print(f"  • Đã đẩy sang Kênh Lẻ  : {copied_le} video")
    print(f"  • Đã đẩy sang Kênh Chẵn: {copied_chan} video")
    print(f"  • Bỏ qua (Đã có sẵn)  : {skipped} video")
    print(f"  • Tổng dung lượng đẩy  : {round(total_bytes / (1024*1024), 1)} MB (~{round(total_bytes / (1024*1024*1024), 2)} GB)")
    print("=" * 65)
    print("[V] Hoàn tất! OneDrive sẽ tự động kéo các video này về Laptop để đăng bài.")
    return {
        "success": True,
        "copied_le": copied_le,
        "copied_chan": copied_chan,
        "skipped": skipped,
        "total_mb": round(total_bytes / (1024*1024), 1)
    }

if __name__ == "__main__":
    sync_videos()
