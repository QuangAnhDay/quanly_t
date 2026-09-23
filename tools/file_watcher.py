import os
import sys
import time
import json
import shutil
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import database

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

class PackageOutputsWatcher(FileSystemEventHandler):
    """
    Theo dõi thư mục outputs/ trọn gói từng kịch bản (outputs/KBxxx/)
    Tự động nhận diện Voice Audio, Video TikTok, Video YouTube, Thumbnail
    """
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        parent_name = os.path.basename(os.path.dirname(file_path))
        
        # Tìm mã kịch bản từ tên folder cha hoặc tên file
        match = re.search(r"(KB\d+)", parent_name, re.IGNORECASE) or re.search(r"(KB\d+)", filename, re.IGNORECASE)
        if not match:
            return
        
        kb_id = match.group(1).upper()
        proj = database.get_project(kb_id)
        if not proj:
            return

        updates = {}
        fn_lower = filename.lower()

        # 1. Nhận diện Audio
        if fn_lower.endswith((".wav", ".mp3", ".m4a")):
            updates["audio_path"] = file_path
            if proj["status"] in ["1_cho_duyet", "2_cho_voice"]:
                updates["status"] = "3_da_co_audio"
            print(f"[Watcher] Gói {kb_id} -> Đã nhận diện Voice Audio: {filename}")

        # 2. Nhận diện Video
        elif fn_lower.endswith((".mp4", ".mov", ".mkv")):
            if "tiktok" in fn_lower or "doc" in fn_lower:
                updates["video_tiktok_path"] = file_path
                updates["video_path"] = file_path
                print(f"[Watcher] Gói {kb_id} -> Đã nhận diện Video TikTok: {filename}")
            elif "youtube" in fn_lower or "ngang" in fn_lower or "yt" in fn_lower:
                updates["video_youtube_path"] = file_path
                if not updates.get("video_path"):
                    updates["video_path"] = file_path
                print(f"[Watcher] Gói {kb_id} -> Đã nhận diện Video YouTube: {filename}")
            else:
                updates["video_path"] = file_path
            
            updates["status"] = "5_hoan_thanh"

        # 3. Nhận diện Thumbnail
        elif fn_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            updates["has_thumbnail"] = 1
            updates["thumbnail_path"] = file_path
            print(f"[Watcher] Gói {kb_id} -> Đã nhận diện Thumbnail: {filename}")

        if updates:
            database.update_project(kb_id, **updates)

class FallbackWatcher(FileSystemEventHandler):
    """Hỗ trợ quét thêm các thư mục phụ cũ nếu người dùng lưu riêng"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
        if not match:
            return
        kb_id = match.group(1).upper()
        
        fn_lower = filename.lower()
        if fn_lower.endswith((".wav", ".mp3", ".m4a")):
            database.update_project(kb_id, audio_path=file_path, status="3_da_co_audio")
        elif fn_lower.endswith((".mp4", ".mov")):
            database.update_project(kb_id, video_path=file_path, status="5_hoan_thanh")
        elif fn_lower.endswith((".png", ".jpg", ".jpeg")):
            database.update_project(kb_id, has_thumbnail=1, thumbnail_path=file_path)

def start_watching():
    outputs_dir = os.path.join(BASE_DIR, "outputs")
    audio_dir = os.path.join(BASE_DIR, "2_audio_input")
    video_dir = os.path.join(BASE_DIR, "3_video_output")
    thumb_dir = os.path.join(BASE_DIR, "4_thumbnails")
    
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)

    observer = Observer()

    # 1. Giám sát chính: Thư mục outputs/ trọn gói từng kịch bản
    observer.schedule(PackageOutputsWatcher(), outputs_dir, recursive=True)
    print(f"[Watcher] Đang theo dõi trọn gói tại: {outputs_dir}")

    # 2. Giám sát phụ các thư mục lẻ
    observer.schedule(FallbackWatcher(), audio_dir, recursive=False)
    observer.schedule(FallbackWatcher(), video_dir, recursive=True)
    observer.schedule(FallbackWatcher(), thumb_dir, recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()
