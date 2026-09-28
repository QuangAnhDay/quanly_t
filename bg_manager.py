import os
import json
import random
from typing import List, Tuple, Optional
import task_logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE_DIR, "data", "bg_rotation_history.json")

def load_rotation_history() -> dict:
    """Đọc lịch sử sử dụng video nền từ file JSON trên ổ đĩa"""
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[BGManager] Lỗi đọc rotation history: {e}")
    return {}

def save_rotation_history(data: dict):
    """Lưu lịch sử sử dụng video nền vào file JSON"""
    try:
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BGManager] Lỗi ghi rotation history: {e}")

def select_smart_background(
    candidates: List[str],
    theme: str = "nau_an",
    orientation: str = "ngang",
    project_id: Optional[str] = None
) -> Tuple[Optional[str], dict]:
    """
    Thuật toán Chống Trùng Nền Thông Minh (Smart Anti-Duplicate & Fair Rotation):
    1. Tránh hoàn toàn N video vừa dùng gần nhất (LRU - Least Recently Used).
    2. Trong số các video còn lại, ưu tiên chọn video có tần suất xuất hiện ít nhất (LFU - Least Frequently Used).
    3. Phân phối đều toàn bộ kho video, ngăn chặn triệt để thuật toán Reused Content của Facebook & TikTok.
    """
    if not candidates:
        return None, {}

    total_candidates = len(candidates)
    if total_candidates == 1:
        # Kho chỉ có 1 video, bắt buộc dùng
        chosen = candidates[0]
        filename = os.path.basename(chosen)
        return chosen, {"filename": filename, "theme": theme, "used_count": 1, "is_single": True}

    category_key = f"{theme}_{orientation}"
    history_all = load_rotation_history()
    category_history = history_all.get(category_key, {
        "recent": [],   # Danh sách tên file đã dùng gần nhất (mới nhất ở đầu)
        "counts": {}    # Số lần từng file được sử dụng
    })

    recent_list = category_history.get("recent", [])
    counts_map = category_history.get("counts", {})

    # Chuẩn hóa tên file để so sánh
    candidate_map = {os.path.basename(c): c for c in candidates}
    available_basenames = list(candidate_map.keys())

    # Tính toán kích thước hàng đợi cấm lặp lại (cooldown window)
    # Ví dụ có 30 video thì cấm 10 video gần nhất; có 5 video thì cấm 2; tối thiểu cấm 1 (không bao giờ trùng clip trước đó)
    cooldown_size = max(1, min(10, total_candidates // 3)) if total_candidates >= 4 else 1
    recent_cooldown = set(recent_list[:cooldown_size])

    # Lọc các video không nằm trong danh sách cấm gần đây
    eligible = [b for b in available_basenames if b not in recent_cooldown]
    if not eligible:
        # Nếu kho nhỏ hơn kích thước cooldown, fallback loại trừ ít nhất video ngay trước đó
        last_used = recent_list[0] if recent_list else None
        eligible = [b for b in available_basenames if b != last_used]
        if not eligible:
            eligible = available_basenames

    # Tìm số lần sử dụng ít nhất trong nhóm eligible
    min_count = min(counts_map.get(b, 0) for b in eligible)

    # Lấy các video có số lần sử dụng ít nhất (ưu tiên cao nhất)
    best_candidates = [b for b in eligible if counts_map.get(b, 0) == min_count]

    # Bốc ngẫu nhiên 1 video trong nhóm tốt nhất này
    chosen_basename = random.choice(best_candidates)
    chosen_path = candidate_map[chosen_basename]

    # Cập nhật số lần dùng và lịch sử gần đây
    new_count = counts_map.get(chosen_basename, 0) + 1
    counts_map[chosen_basename] = new_count

    # Đưa vào đầu danh sách recent (giữ tối đa 30 mục)
    new_recent = [chosen_basename] + [b for b in recent_list if b != chosen_basename]
    category_history["recent"] = new_recent[:30]
    category_history["counts"] = counts_map
    history_all[category_key] = category_history

    save_rotation_history(history_all)

    # Ghi log real-time
    msg = f"🎯 [Chống Trùng Nền] Đã bốc thông minh clip ít dùng: {chosen_basename} (đã dùng {new_count} lần, tránh trùng {len(recent_cooldown)} clip gần nhất)"
    task_logger.add_log("capcut", msg, "info", project_id)
    try:
        print(f"[BGManager] {msg}")
    except Exception:
        print(f"[BGManager] Chon clip nen: {chosen_basename} (lan {new_count})")

    meta = {
        "filename": chosen_basename,
        "theme": theme,
        "orientation": orientation,
        "used_count": new_count,
        "cooldown_applied": len(recent_cooldown)
    }
    return chosen_path, meta
