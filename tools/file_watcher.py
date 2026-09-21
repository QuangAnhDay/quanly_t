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
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

class AudioInputFolderWatcher(FileSystemEventHandler):
    """Theo dõi trực tiếp thư mục 2_audio_input: Khi bạn lưu file KBxxx.wav/.mp3 vào đây"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        if filename.lower().endswith((".wav", ".mp3")):
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            if match:
                kb_id = match.group(1).upper()
                proj = database.get_project(kb_id)
                if proj and (not proj.get("audio_path") or proj["status"] in ["1_cho_duyet", "2_cho_voice"]):
                    database.update_project(kb_id, audio_path=file_path, status="3_da_co_audio")
                    print(f"[Watcher] Đã phát hiện file audio trực tiếp và cập nhật {kb_id} -> '3_da_co_audio'")

class VoiceStudioWatcher(FileSystemEventHandler):
    """Theo dõi thư mục xuất của VoiceStudio và tự động bốc sang 2_audio_input"""
    def __init__(self, target_audio_dir):
        self.target_audio_dir = target_audio_dir

    def on_created(self, event):
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path)
        if filename.lower().endswith((".wav", ".mp3")):
            print(f"[Watcher] Phát hiện file mới từ VoiceStudio: {filename}")
            time.sleep(1.0)
            
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            target_kb_id = None
            if match:
                target_kb_id = match.group(1).upper()
            else:
                projects = database.get_all_projects()
                for p in projects:
                    if p["status"] in ["2_cho_voice", "1_cho_duyet"]:
                        target_kb_id = p["id"]
                        break
            
            if target_kb_id:
                dest_name = f"{target_kb_id}.wav"
                dest_path = os.path.join(self.target_audio_dir, dest_name)
                try:
                    shutil.copy2(event.src_path, dest_path)
                    database.update_project(target_kb_id, audio_path=dest_path, status="3_da_co_audio")
                    print(f"[Watcher] Đã tự động gán file vào {target_kb_id} -> {dest_path}")
                except Exception as e:
                    print(f"[Watcher] Lỗi khi copy file: {e}")

class CapCutVideoWatcher(FileSystemEventHandler):
    """Theo dõi thư mục 3_video_output khi CapCut xuất file KBxxx.mp4"""
    def on_created(self, event):
        self.handle_file(event.src_path)

    def on_modified(self, event):
        self.handle_file(event.src_path)

    def handle_file(self, file_path):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        if filename.lower().endswith(".mp4"):
            match = re.search(r"(KB\d+)", filename, re.IGNORECASE)
            if match:
                kb_id = match.group(1).upper()
                database.update_project(kb_id, video_path=file_path, status="5_hoan_thanh")
                print(f"[Watcher] Đã cập nhật trạng thái {kb_id} thành '5_hoan_thanh'!")

def start_watching():
    config = load_config()
    audio_dir = os.path.join(BASE_DIR, "2_audio_input")
    video_dir = os.path.join(BASE_DIR, "3_video_output")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)

    observer = Observer()

    # 1. Theo dõi thư mục 2_audio_input (nơi bạn tự lưu file KBxxx.wav từ repo)
    observer.schedule(AudioInputFolderWatcher(), audio_dir, recursive=False)
    print(f"[Watcher] Đang theo dõi thư mục Audio trực tiếp tại: {audio_dir}")

    # 2. Theo dõi thư mục output của VoiceStudio (nếu có)
    vs_dir = config.get("voicestudio_output_dir", "")
    if os.path.exists(vs_dir):
        print(f"[Watcher] Đang theo dõi thư mục VoiceStudio tại: {vs_dir}")
        observer.schedule(VoiceStudioWatcher(audio_dir), vs_dir, recursive=False)

    # 3. Theo dõi thư mục 3_video_output (CapCut xuất video)
    observer.schedule(CapCutVideoWatcher(), video_dir, recursive=False)
    print(f"[Watcher] Đang theo dõi thư mục Video Output tại: {video_dir}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()
