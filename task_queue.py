import os
import sys
import time
import queue
import threading
import traceback
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

import database
import audio_engine
import capcut_engine
import video_engine
import task_logger

# Cấu trúc lưu trữ Hàng Đợi Công Việc
_task_queue = queue.Queue()
_lock = threading.Lock()

_running_task: Optional[Dict[str, Any]] = None
_finished_tasks: List[Dict[str, Any]] = []
_task_counter = 0

MAX_FINISHED_TASKS = 100

def get_next_task_id() -> str:
    global _task_counter
    with _lock:
        _task_counter += 1
        return f"TASK_{_task_counter:04d}"

def add_task(task_type: str, project_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Thêm 1 công việc ngầm vào Hàng Đợi:
    - task_type: 'audio', 'capcut', 'tiktok', 'split_parts'
    - project_id: mã kịch bản KBxxx
    - payload: tham số bổ sung (voice, rate, pitch, theme, style, part_duration...)
    """
    task_id = get_next_task_id()
    now_str = datetime.now().strftime("%H:%M:%S")
    
    proj = database.get_project(project_id)
    proj_title = proj.get("title", project_id) if proj else project_id
    
    task_item = {
        "id": task_id,
        "type": task_type.lower(),
        "project_id": project_id,
        "project_title": proj_title,
        "payload": payload or {},
        "status": "queued", # queued, running, completed, failed
        "progress": 0,
        "message": "Đang chờ trong hàng đợi...",
        "created_at": now_str,
        "started_at": None,
        "finished_at": None,
        "error": None
    }
    
    _task_queue.put(task_item)
    
    type_names = {
        "audio": "Tạo Voice Audio",
        "capcut": "Tạo CapCut 16:9",
        "tiktok": "Chuyển TikTok 9:16",
        "split_parts": "Cắt tập nhỏ"
    }
    t_name = type_names.get(task_type.lower(), task_type)
    task_logger.add_log(
        module=task_type.lower(),
        message=f"📥 Đã thêm [{project_id}] vào hàng đợi xử lý ngầm ({t_name})",
        level="info",
        project_id=project_id
    )
    
    return task_item

def add_batch_tasks(task_type: str, project_ids: List[str], payload: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Thêm hàng loạt công việc vào Hàng Đợi cùng lúc"""
    added = []
    for pid in project_ids:
        t = add_task(task_type, pid, payload)
        added.append(t)
    return added

def get_queue_status() -> Dict[str, Any]:
    """Trả về trạng thái toàn bộ Hàng Đợi hiện tại"""
    with _lock:
        running = _running_task.copy() if _running_task else None
        finished = list(_finished_tasks)
    
    # Lấy danh sách đang chờ trong Queue
    queued_list = list(_task_queue.queue)
    
    return {
        "running_task": running,
        "queued_tasks": queued_list,
        "finished_tasks": finished[-20:], # 20 tác vụ gần nhất
        "stats": {
            "queued_count": len(queued_list),
            "is_running": running is not None,
            "total_finished": len(finished)
        }
    }

def clear_queued_tasks() -> int:
    """Xóa tất cả các tác vụ đang chờ trong Hàng Đợi (giữ tác vụ đang chạy)"""
    count = 0
    with _task_queue.mutex:
        count = len(_task_queue.queue)
        _task_queue.queue.clear()
    
    if count > 0:
        task_logger.add_log("system", f"🧹 Đã dọn dẹp {count} công việc trong hàng đợi", "info")
    return count

def _process_audio_task(task: Dict[str, Any]):
    project_id = task["project_id"]
    payload = task["payload"]
    
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Không tìm thấy kịch bản {project_id}")
    if not proj.get("content"):
        raise ValueError(f"Kịch bản {project_id} chưa có nội dung văn bản")
        
    pkg_dir = database.get_package_dir(project_id)
    pkg_audio_path = os.path.join(pkg_dir, f"{project_id}_voice.mp3")
    
    voice_used = payload.get("voice") or proj.get("voice") or "vi-VN-HoaiMyNeural"
    rate = payload.get("rate") or proj.get("rate") or "+0%"
    pitch = payload.get("pitch") or proj.get("pitch") or "+0Hz"
    
    def on_chunk_progress(current: int, total: int):
        task["chunk_current"] = current
        task["chunk_total"] = total
        task["progress"] = int((current / total) * 100)
        task["message"] = f"Đang tạo đoạn ({current}/{total})"

    task["message"] = f"Đang phân đoạn kịch bản..."
    task_logger.add_log("audio", f"🎙️ [Hàng Đợi] Đang chuẩn bị tạo Voice Audio cho [{project_id}] ({voice_used})...", "info", project_id)
    
    # Chạy hàm async generate_speech đồng bộ trong thread ngầm
    actual_path = asyncio.run(audio_engine.generate_speech(
        text=proj["content"],
        output_path=pkg_audio_path,
        voice=voice_used,
        rate=rate,
        pitch=pitch,
        on_progress=on_chunk_progress
    ))
    
    database.update_project(
        project_id,
        audio_path=actual_path,
        voice=voice_used,
        rate=rate,
        pitch=pitch,
        status="3_da_co_audio"
    )
    
    task_logger.add_log("audio", f"✅ [Hàng Đợi] Đã tạo xong Voice Audio cho [{project_id}]!", "success", project_id)
    return {"audio_path": actual_path}

def _process_capcut_task(task: Dict[str, Any]):
    project_id = task["project_id"]
    payload = task["payload"]
    
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Không tìm thấy kịch bản {project_id}")
    audio_path = proj.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        raise ValueError(f"Kịch bản {project_id} chưa có file Audio")
        
    theme = payload.get("theme") or "nau_an"
    theme_names = {"nau_an": "Nấu ăn", "handmade": "Handmade"}
    theme_vn = theme_names.get(theme, theme)
    
    task["message"] = f"Đang khớp clip nền CapCut ({theme_vn})..."
    task_logger.add_log("capcut", f"🎬 [Hàng Đợi] Đang tạo Dự Án CapCut 16:9 cho [{project_id}]...", "info", project_id)
    
    draft_res = capcut_engine.create_capcut_draft(
        project_id=project_id,
        title=proj["title"],
        audio_path=audio_path,
        theme=theme
    )
    
    draft_name = draft_res["draft_name"]
    notes = f"CapCut ({theme_vn}): {draft_name}"
    
    database.update_project(
        project_id,
        capcut_draft_youtube=draft_name,
        notes=notes,
        status="4_da_render_video"
    )
    
    task_logger.add_log("capcut", f"🎬 [Hàng Đợi] Đã hoàn thành CapCut 16:9 cho [{project_id}] ({draft_res['clips_count']} clip nền)", "success", project_id)
    return draft_res

def _process_tiktok_task(task: Dict[str, Any]):
    project_id = task["project_id"]
    payload = task["payload"]
    
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Không tìm thấy kịch bản {project_id}")
        
    style = payload.get("style", "blur")
    
    src_video = proj.get("video_youtube_path") or proj.get("video_path")
    if not src_video or not os.path.exists(src_video):
        pkg_dir = os.path.join(database.BASE_DIR, "outputs", project_id)
        if os.path.exists(pkg_dir):
            for f in os.listdir(pkg_dir):
                if f.lower().endswith((".mp4", ".mov")) and "tiktok" not in f.lower() and "doc" not in f.lower():
                    src_video = os.path.join(pkg_dir, f)
                    break
                    
    if not src_video or not os.path.exists(src_video):
        raise ValueError(f"Chưa có video ngang (YouTube) để chuyển đổi cho [{project_id}]")
        
    pkg_dir = database.get_package_dir(project_id)
    out_tiktok_path = os.path.join(pkg_dir, f"{project_id}_tiktok.mp4")
    
    task["message"] = "Đang chuyển đổi video 16:9 sang 9:16 TikTok (Cinematic Blur)..."
    task_logger.add_log("tiktok", f"📱 [Hàng Đợi] Đang chuyển đổi TikTok 9:16 cho [{project_id}]...", "info", project_id)
    
    video_engine.convert_16x9_to_9x16(src_video, out_tiktok_path, style=style)
    
    database.update_project(
        project_id,
        video_tiktok_path=out_tiktok_path,
        status="5_hoan_thanh"
    )
    
    task_logger.add_log("tiktok", f"📱 [Hàng Đợi] Đã tạo xong video TikTok 9:16 cho [{project_id}]!", "success", project_id)
    return {"video_tiktok_path": out_tiktok_path}

def _process_split_parts_task(task: Dict[str, Any]):
    project_id = task["project_id"]
    payload = task["payload"]
    
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Không tìm thấy kịch bản {project_id}")
        
    part_dur = payload.get("part_duration_sec", 180)
    src_video = proj.get("video_tiktok_path") or proj.get("video_youtube_path") or proj.get("video_path")
    if not src_video or not os.path.exists(src_video):
        raise ValueError(f"Chưa có video nguồn để cắt tập cho [{project_id}]")
        
    pkg_dir = os.path.join(database.BASE_DIR, "outputs", project_id, "parts")
    os.makedirs(pkg_dir, exist_ok=True)
    
    task["message"] = f"Đang cắt video thành các Part ngắn {part_dur}s..."
    task_logger.add_log("tiktok", f"✂️ [Hàng Đợi] Đang cắt video ngắn cho [{project_id}]...", "info", project_id)
    
    parts = video_engine.split_video_into_parts(
        input_video_path=src_video,
        output_dir=pkg_dir,
        part_prefix=project_id,
        part_duration_sec=part_dur
    )
    
    task_logger.add_log("tiktok", f"✂️ [Hàng Đợi] Đã cắt thành công {len(parts)} tập ngắn cho [{project_id}]!", "success", project_id)
    return {"parts_count": len(parts), "parts": parts}

def _process_claude_task(task: Dict[str, Any]):
    project_id = task["project_id"]
    payload = task["payload"] or {}
    
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Không tìm thấy kịch bản {project_id}")
        
    raw_content = proj.get("raw_content") or proj.get("content")
    if not raw_content:
        raise ValueError(f"Kịch bản [{project_id}] chưa có nội dung thô!")
        
    def on_progress(msg: str, progress: int, word_count: int):
        task["progress"] = progress
        task["message"] = msg
        if word_count > 0:
            task["word_count"] = word_count
            
    task["message"] = "Đang chạy Claude Engine ngầm..."
    task_logger.add_log("claude", f"🤖 [Hàng Đợi] Bắt đầu tự động hóa Claude ngầm cho [{project_id}]...", "info", project_id)
    
    import claude_engine
    result = asyncio.run(claude_engine.run_claude_2skill_backend(
        project_id=project_id,
        raw_content=raw_content,
        on_progress=on_progress
    ))
    
    database.complete_raw_project(
        project_id=project_id,
        title=result["title"],
        content=result["content"],
        thumb_prompt=result.get("thumb_prompt", ""),
        notes=f"Claude Engine ({result.get('mode', 'backend')}) hoàn tất ({result.get('word_count', 0)} từ)"
    )
    
    task_logger.add_log("claude", f"✅ [Hàng Đợi] Đã sinh thành công Kịch bản & Thumb ngầm cho [{project_id}] ({result.get('word_count', 0)} từ)!", "success", project_id)
    return result

def _worker_loop():
    """Vòng lặp Worker chính chạy ngầm xử lý từng công việc tuần tự"""
    global _running_task, _finished_tasks
    
    while True:
        try:
            task = _task_queue.get(block=True, timeout=1.0)
        except queue.Empty:
            time.sleep(0.5)
            continue
            
        with _lock:
            task["status"] = "running"
            task["started_at"] = datetime.now().strftime("%H:%M:%S")
            task["progress"] = 10
            _running_task = task

        task_id = task["id"]
        task_type = task["type"]
        project_id = task["project_id"]
        
        try:
            if task_type == "audio":
                res = _process_audio_task(task)
            elif task_type == "capcut":
                res = _process_capcut_task(task)
            elif task_type == "tiktok":
                res = _process_tiktok_task(task)
            elif task_type == "split_parts":
                res = _process_split_parts_task(task)
            elif task_type == "claude":
                res = _process_claude_task(task)
            else:
                raise ValueError(f"Loại công việc không hợp lệ: {task_type}")
                
            with _lock:
                task["status"] = "completed"
                task["progress"] = 100
                task["finished_at"] = datetime.now().strftime("%H:%M:%S")
                task["message"] = "Đã hoàn thành xuất sắc!"
                task["result"] = res
                
        except Exception as e:
            err_msg = str(e)
            print(f"[TaskQueue Error] Lỗi khi xử lý {task_id} ({task_type} - {project_id}): {err_msg}")
            traceback.print_exc()
            
            with _lock:
                task["status"] = "failed"
                task["progress"] = 0
                task["finished_at"] = datetime.now().strftime("%H:%M:%S")
                task["message"] = f"Lỗi: {err_msg}"
                task["error"] = err_msg
                
            task_logger.add_log(task_type, f"❌ [Hàng Đợi] Lỗi khi xử lý [{project_id}]: {err_msg}", "error", project_id)
            
        finally:
            with _lock:
                _finished_tasks.append(task)
                if len(_finished_tasks) > MAX_FINISHED_TASKS:
                    _finished_tasks.pop(0)
                _running_task = None
            _task_queue.task_done()

# Khởi chạy Worker Thread khi import module
_worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="TaskQueueWorker")
_worker_thread.start()
