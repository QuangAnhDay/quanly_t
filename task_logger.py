import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import threading

_log_lock = threading.Lock()
_log_counter = 0
_logs_buffer: List[Dict[str, Any]] = []
MAX_LOG_ENTRIES = 300

MODULE_ICONS = {
    "audio": "🎙️",
    "capcut": "🎬",
    "tiktok": "📱",
    "thumb": "🖼️",
    "claude": "🤖",
    "system": "⚙️"
}

def add_log(module: str, message: str, level: str = "info", project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Thêm 1 nhật ký hoạt động mới vào hệ thống.
    module: 'audio', 'capcut', 'tiktok', 'thumb', 'claude', 'system'
    level: 'info', 'success', 'warning', 'error'
    """
    global _log_counter, _logs_buffer
    with _log_lock:
        _log_counter += 1
        now = datetime.now()
        entry = {
            "id": _log_counter,
            "timestamp": now.strftime("%H:%M:%S"),
            "date": now.strftime("%d/%m/%Y"),
            "module": module.lower(),
            "level": level.lower(),
            "message": message,
            "project_id": project_id or "",
            "icon": MODULE_ICONS.get(module.lower(), "📝")
        }
        _logs_buffer.append(entry)
        if len(_logs_buffer) > MAX_LOG_ENTRIES:
            _logs_buffer.pop(0)
        return entry

def get_logs(limit: int = 100, since_id: int = 0, module: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách nhật ký hoạt động gần nhất"""
    with _log_lock:
        filtered = _logs_buffer
        if since_id > 0:
            filtered = [x for x in filtered if x["id"] > since_id]
        if module and module != "all":
            filtered = [x for x in filtered if x["module"] == module.lower()]
        return filtered[-limit:]

def clear_logs():
    """Xóa sạch nhật ký hoạt động"""
    global _logs_buffer
    with _log_lock:
        _logs_buffer.clear()

# Khởi tạo 1 log ban đầu thông báo hệ thống hoạt động
add_log("system", "Hệ thống Quản lý Truyện Automation sẵn sàng giám sát", "info")
