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
    và tự động đồng bộ khi file được tạo, sửa hoặc BỊ XÓA.
    """
    def on_created(self, event):
        self.handle_event(event.src_path, "tạo mới")

    def on_modified(self, event):
        self.handle_event(event.src_path, "cập nhật")

    def on_deleted(self, event):
        self.handle_event(event.src_path, "đã xóa")

    def handle_event(self, file_path, action_name=""):
        if os.path.isdir(file_path):
            return
        filename = os.path.basename(file_path)
        parent_name = os.path.basename(os.path.dirname(file_path))
        
        # Tìm mã kịch bản từ tên folder cha hoặc tên file
        match = re.search(r"(KB\d+)", parent_name, re.IGNORECASE) or re.search(r"(KB\d+)", filename, re.IGNORECASE)
        if not match:
            return
        
        kb_id = match.group(1).upper()
        # Đồng bộ trực tiếp và chuẩn xác với ổ đĩa thực tế
        proj = database.sync_project_files(kb_id)
        if proj:
            print(f"[Watcher] Gói {kb_id} -> File {filename} {action_name}. Đã đồng bộ DB.")

def start_watching():
    outputs_dir = os.path.join(BASE_DIR, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    observer = Observer()
    # Giám sát duy nhất: Thư mục outputs/ trọn gói từng kịch bản
    observer.schedule(PackageOutputsWatcher(), outputs_dir, recursive=True)
    print(f"[Watcher] Đang theo dõi duy nhất tại: {outputs_dir}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()

