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

class AudioInputFolderWatcher(FileSystemEventHandler):
    """Theo dõi thư mục 2_audio_input: Khi bạn lưu file KBxxx.wav/.mp3 vào đây"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        if filename.lower().endswith((".wav", ".mp3", ".m4a")):
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            if match:
                kb_id = match.group(1).upper()
                proj = database.get_project(kb_id)
                if proj and (not proj.get("audio_path") or proj["status"] in ["1_cho_duyet", "2_cho_voice"]):
                    database.update_project(kb_id, audio_path=file_path, status="3_da_co_audio")
                    print(f"[Watcher] Đã phát hiện file audio và cập nhật {kb_id} -> '3_da_co_audio'")

class VideoOutputWatcher(FileSystemEventHandler):
    """Theo dõi thư mục 3_video_output và các thư mục con tiktok/, youtube/"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        if filename.lower().endswith((".mp4", ".mov", ".mkv")):
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            if match:
                kb_id = match.group(1).upper()
                parent_dir = os.path.basename(os.path.dirname(file_path)).lower()
                
                updates = {}
                # Nhận diện theo thư mục con hoặc tên file
                if parent_dir == "tiktok" or "tiktok" in filename.lower() or "doc" in filename.lower():
                    updates["video_tiktok_path"] = file_path
                    updates["video_path"] = file_path
                    print(f"[Watcher] Đã nhận diện Video TikTok cho {kb_id}")
                elif parent_dir == "youtube" or "youtube" in filename.lower() or "ngang" in filename.lower() or "yt" in filename.lower():
                    updates["video_youtube_path"] = file_path
                    if not updates.get("video_path"):
                        updates["video_path"] = file_path
                    print(f"[Watcher] Đã nhận diện Video YouTube cho {kb_id}")
                else:
                    # Video lưu ở thư mục gốc 3_video_output
                    updates["video_path"] = file_path

                updates["status"] = "5_hoan_thanh"
                database.update_project(kb_id, **updates)
                print(f"[Watcher] Cập nhật tiến độ {kb_id} -> Video sẵn sàng!")

class ThumbnailWatcher(FileSystemEventHandler):
    """Theo dõi thư mục 4_thumbnails: Tự động tích xanh khi có ảnh Thumb"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            if match:
                kb_id = match.group(1).upper()
                database.update_project(kb_id, has_thumbnail=1, thumbnail_path=file_path)
                print(f"[Watcher] Đã phát hiện Thumbnail cho {kb_id} -> Bật tích xanh!")

def start_watching():
    audio_dir = os.path.join(BASE_DIR, "2_audio_input")
    video_dir = os.path.join(BASE_DIR, "3_video_output")
    thumb_dir = os.path.join(BASE_DIR, "4_thumbnails")
    
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(os.path.join(video_dir, "tiktok"), exist_ok=True)
    os.makedirs(os.path.join(video_dir, "youtube"), exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)

    observer = Observer()

    # 1. Theo dõi thư mục Audio
    observer.schedule(AudioInputFolderWatcher(), audio_dir, recursive=False)
    print(f"[Watcher] Đang theo dõi Audio tại: {audio_dir}")

    # 2. Theo dõi thư mục Video Output (bao gồm cả tiktok/ và youtube/)
    observer.schedule(VideoOutputWatcher(), video_dir, recursive=True)
    print(f"[Watcher] Đang theo dõi Video Output tại: {video_dir}")

    # 3. Theo dõi thư mục Thumbnail
    observer.schedule(ThumbnailWatcher(), thumb_dir, recursive=True)
    print(f"[Watcher] Đang theo dõi Thumbnail tại: {thumb_dir}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()
