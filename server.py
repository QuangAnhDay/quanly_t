import os
import sys
import json
import subprocess
import glob
import re
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import database
import audio_engine
import video_engine
import thumbnail_engine
import capcut_engine
import task_queue

# Khởi tạo toàn bộ thư mục cần thiết
capcut_engine.init_theme_folders()
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)

# Khởi tạo DB
database.init_db()

app = FastAPI(title="Xưởng Sản Xuất Video Audio - Truyện Automation")

@app.on_event("startup")
async def startup_event():
    try:
        import voicestudio_service
        import task_logger
        task_logger.add_log("system", "Hệ thống Web Dashboard đã khởi động thành công", "info")
        vs_ready = voicestudio_service.ensure_voicestudio_running()
        if vs_ready:
            task_logger.add_log("system", "VoiceStudio API Server (Port 3900) đã sẵn sàng", "success")
        else:
            task_logger.add_log("system", "VoiceStudio Server chưa bật tại D:\\myProject\\voice", "warning")
    except Exception as e:
        print(f"[Startup] Lỗi kiểm tra VoiceStudio: {e}")

# Cho phép CORS để Tampermonkey từ claude.ai gọi được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_detected_chrome_profiles():
    """Đọc file Local State của Chrome để lấy danh sách hồ sơ chuẩn xác với Email và Tên hiển thị"""
    local_state_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State")
    profiles = []
    if os.path.exists(local_state_path):
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            for folder, info in info_cache.items():
                profiles.append({
                    "id": folder,
                    "name": info.get("name", folder),
                    "email": info.get("user_name", ""),
                    "gaia_name": info.get("gaia_name", ""),
                })
        except Exception as e:
            print(f"Lỗi đọc Chrome Local State: {e}")
    return profiles

def auto_sync_disk_files():
    """Tự động kiểm tra gói outputs/KBxxx và các thư mục liên quan để cập nhật trạng thái chuẩn xác"""
    return database.sync_all_projects()


class ScriptPayload(BaseModel):
    title: str
    content: str
    voice: Optional[str] = "vi-VN-HoaiMyNeural"
    notes: Optional[str] = ""

class AudioGenPayload(BaseModel):
    voice: Optional[str] = "vi-VN-HoaiMyNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class RenderVideoPayload(BaseModel):
    aspect_ratio: Optional[str] = "9:16"

class ThumbGenPayload(BaseModel):
    prompt: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"

class LaunchSelectedProfilesPayload(BaseModel):
    profiles: List[str]

class CapCutDraftPayload(BaseModel):
    theme: Optional[str] = "nau_an"

class BatchCapCutPayload(BaseModel):
    project_ids: List[str]
    theme: Optional[str] = "nau_an"

class RawScriptPayload(BaseModel):
    raw_content: str
    title: Optional[str] = None
    notes: Optional[str] = ""

class BatchRawScriptPayload(BaseModel):
    raw_scripts: List[str]

class AICompletePayload(BaseModel):
    title: str
    content: str
    thumb_prompt: Optional[str] = ""
    notes: Optional[str] = ""

class ClaudeSkillConfigPayload(BaseModel):
    script_skill_command: str
    title_thumb_skill_command: str

class BatchDeletePayload(BaseModel):
    project_ids: List[str]

class OpenFilePayload(BaseModel):
    file_path: str

class ConvertTikTokPayload(BaseModel):
    style: Optional[str] = "blur"

class SplitPartsPayload(BaseModel):
    part_duration_sec: Optional[int] = 180

class DispatchClaudePayload(BaseModel):
    profiles: Optional[List[str]] = None
    project_ids: Optional[List[str]] = None
    profile_count: Optional[int] = 5

class QueueTaskPayload(BaseModel):
    task_type: str
    project_id: Optional[str] = None
    project_ids: Optional[List[str]] = None
    payload: Optional[dict] = None

@app.get("/api/queue/status")
async def get_queue_status_api():
    """Trả về trạng thái tiến trình các tác vụ trong Hàng Đợi Ngầm"""
    return task_queue.get_queue_status()

@app.post("/api/queue/add")
async def add_queue_task_api(payload: QueueTaskPayload):
    """Thêm 1 hoặc hàng loạt tác vụ vào Hàng Đợi Ngầm xử lý tuần tự"""
    if payload.project_ids and len(payload.project_ids) > 0:
        tasks = task_queue.add_batch_tasks(payload.task_type, payload.project_ids, payload.payload)
        return {"success": True, "queued": True, "queued_count": len(tasks), "tasks": tasks}
    elif payload.project_id:
        t = task_queue.add_task(payload.task_type, payload.project_id, payload.payload)
        return {"success": True, "queued": True, "task": t}
    else:
        raise HTTPException(status_code=400, detail="Vui lòng chọn kịch bản để thêm vào hàng đợi")

@app.post("/api/queue/clear")
async def clear_queue_api():
    """Dọn dẹp danh sách các tác vụ đang chờ trong Hàng Đợi Ngầm"""
    count = task_queue.clear_queued_tasks()
    return {"success": True, "cleared_count": count}

@app.get("/claude_to_truyen.user.js")
async def get_userscript_file():
    """Endpoint giúp cài đặt hoặc cập nhật Tampermonkey Userscript 1-Click"""
    js_path = os.path.join(BASE_DIR, "tools", "claude_to_truyen.user.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="text/javascript")
    raise HTTPException(status_code=404, detail="Không tìm thấy file Userscript")





@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(BASE_DIR, "web", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Đang thiết lập Web Dashboard...</h1>"

@app.get("/api/config")
async def api_get_config():
    return get_config()

@app.get("/api/themes")
async def api_get_themes():
    """Lấy số lượng clip trong kho chi tiết theo chủ đề và định dạng (dọc / ngang)"""
    return capcut_engine.get_theme_stats()

@app.get("/api/chrome-profiles")
async def api_get_chrome_profiles():
    return get_detected_chrome_profiles()

@app.post("/api/launch-chrome-selected")
async def api_launch_chrome_selected(payload: LaunchSelectedProfilesPayload):
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")

    launched = []
    for pid in payload.profiles:
        cmd = f'"{chrome_path}" --profile-directory="{pid}" "https://claude.ai"'
        subprocess.Popen(cmd, shell=True)
        launched.append(pid)
    
    return {"success": True, "launched": launched, "count": len(launched)}

@app.get("/api/voices")
async def api_get_voices():
    """Trả về danh sách giọng đọc Edge-TTS + giọng clone cá nhân từ VoiceStudio"""
    voices = [
        {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (Nữ - Edge-TTS)", "type": "edge_tts"},
        {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (Nam - Edge-TTS)", "type": "edge_tts"},
    ]
    try:
        import voicestudio_service
        cloned = voicestudio_service.get_voicestudio_voices()
        for v in cloned:
            voice_id = v.get("voice_id") or v.get("id") or ""
            voice_name = v.get("name") or voice_id
            if voice_id:
                voices.append({
                    "id": f"voicestudio:{voice_id}",
                    "name": f"🎙️ {voice_name} (Clone)",
                    "type": "voicestudio"
                })
    except Exception as e:
        print(f"[/api/voices] Không đọc được giọng VoiceStudio: {e}")
    return {"voices": voices}

@app.get("/api/system/health")
async def api_system_health():
    """Endpoint giám sát sức khỏe hệ thống: VoiceStudio, ổ đĩa, kho ảnh, kho video nền"""
    import shutil
    import time as _time

    # 1. VoiceStudio
    vs_info = {"online": False, "ready": False, "voice_count": 0, "voices": [], "latency_ms": None}
    try:
        import voicestudio_service
        t0 = _time.perf_counter()
        vs_online = voicestudio_service.is_voicestudio_available()
        latency = round((_time.perf_counter() - t0) * 1000, 1)
        vs_info["online"] = vs_online
        vs_info["latency_ms"] = latency
        if vs_online:
            cloned = voicestudio_service.get_voicestudio_voices()
            vs_info["ready"] = True
            vs_info["voice_count"] = len(cloned)
            vs_info["voices"] = [{"id": v.get("voice_id") or v.get("id", ""), "name": v.get("name", "")} for v in cloned]
    except Exception as e:
        vs_info["error"] = str(e)

    # 2. Disk usage
    try:
        usage = shutil.disk_usage(BASE_DIR)
        free_gb = round(usage.free / (1024**3), 2)
        total_gb = round(usage.total / (1024**3), 2)
        used_pct = round((usage.used / usage.total) * 100, 1)
        disk_info = {
            "free_gb": free_gb,
            "total_gb": total_gb,
            "used_percent": used_pct,
            "low_space_warning": free_gb < 5
        }
    except Exception:
        disk_info = {"free_gb": 0, "total_gb": 0, "used_percent": 0, "low_space_warning": True}

    # 3. Thumbnail assets
    thumb_dir = os.path.join(BASE_DIR, "thumb_assets")
    thumb_count = 0
    if os.path.isdir(thumb_dir):
        thumb_count = len([f for f in os.listdir(thumb_dir) if os.path.isfile(os.path.join(thumb_dir, f))])

    # 4. Background video stats
    bg_stats = {}
    try:
        bg_stats = capcut_engine.get_theme_stats()
    except Exception:
        pass

    return {
        "voicestudio": vs_info,
        "storage": disk_info,
        "thumb_assets": {"count": thumb_count},
        "background_videos": bg_stats
    }

@app.get("/api/system/activity-logs")
async def get_activity_logs_api(limit: int = 100, since_id: int = 0, module: Optional[str] = None):
    import task_logger
    logs = task_logger.get_logs(limit=limit, since_id=since_id, module=module)
    return {"logs": logs, "count": len(logs)}

@app.delete("/api/system/activity-logs")
async def clear_activity_logs_api():
    import task_logger
    task_logger.clear_logs()
    task_logger.add_log("system", "Đã xóa sạch nhật ký hoạt động hệ thống", "info")
    return {"success": True}

@app.get("/api/projects")
async def list_projects():
    auto_sync_disk_files()
    return database.get_all_projects()

@app.post("/api/projects")
async def create_project_api(payload: ScriptPayload):
    proj = database.create_project(
        title=payload.title,
        content=payload.content,
        status="1_cho_duyet",
        voice=payload.voice,
        notes=payload.notes
    )
    return proj

@app.get("/api/claude-skill-config")
async def api_get_claude_skill_config():
    cfg = get_config()
    skills = cfg.get("claude_skills", {
        "script_skill_command": "/tao-kich-ban",
        "title_thumb_skill_command": "/tieu-de-thumb"
    })
    return skills

@app.post("/api/claude-skill-config")
async def api_set_claude_skill_config(payload: ClaudeSkillConfigPayload):
    cfg = get_config()
    cfg["claude_skills"] = {
        "script_skill_command": payload.script_skill_command.strip(),
        "title_thumb_skill_command": payload.title_thumb_skill_command.strip()
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return {"success": True, "claude_skills": cfg["claude_skills"]}

@app.get("/api/projects/pending-raw")
async def get_pending_raw():
    """Lấy danh sách các kịch bản thô chưa hoàn thiện"""
    return database.get_pending_raw_projects()

@app.post("/api/projects/create-raw")
async def create_raw_project_api(payload: RawScriptPayload):
    proj = database.create_raw_project(
        raw_content=payload.raw_content,
        title=payload.title,
        notes=payload.notes
    )
    return proj

@app.post("/api/projects/batch-create-raw")
async def batch_create_raw_api(payload: BatchRawScriptPayload):
    projs = database.batch_create_raw_projects(payload.raw_scripts)
    return {"success": True, "count": len(projs), "projects": projs}

@app.post("/api/projects/{project_id}/ai-complete")
async def complete_raw_by_ai(project_id: str, payload: AICompletePayload):
    """Cập nhật kịch bản sau khi Claude chạy xong 2 Skill"""
    proj = database.complete_raw_project(
        project_id=project_id,
        title=payload.title,
        content=payload.content,
        thumb_prompt=payload.thumb_prompt or "",
        notes=payload.notes or ""
    )
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    return {"success": True, "project": proj}

@app.post("/api/dispatch-claude-batch")
async def dispatch_claude_batch_api(payload: DispatchClaudePayload):
    """Mở chính xác các profile Chrome đã chọn và tự động gán kịch bản thô tương ứng"""
    cfg = get_config()
    
    # Ưu tiên danh sách profile gửi từ giao diện web
    if payload.profiles and len(payload.profiles) > 0:
        selected_profiles = payload.profiles
    else:
        profiles = cfg.get("chrome_profiles", ["Profile 7", "Profile 2", "Profile 4", "Profile 5", "Profile 1"])
        count = min(payload.profile_count or 5, len(profiles))
        selected_profiles = profiles[:count]

    # Lấy danh sách kịch bản thô cần xử lý
    if payload.project_ids and len(payload.project_ids) > 0:
        pending_list = [database.get_project(pid) for pid in payload.project_ids if database.get_project(pid)]
    else:
        pending_list = database.get_pending_raw_projects()

    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")

    launched = []
    for idx, pid in enumerate(selected_profiles):
        target_kb = pending_list[idx]["id"] if idx < len(pending_list) else None
        target_url = f"https://claude.ai/new?auto_kb={target_kb}" if target_kb else "https://claude.ai/new"
        cmd = f'"{chrome_path}" --profile-directory="{pid}" "{target_url}"'
        subprocess.Popen(cmd, shell=True)
        launched.append({"profile": pid, "assigned_kb": target_kb})

    return {
        "success": True,
        "launched": launched,
        "count": len(launched),
        "message": f"Đã mở {len(launched)} Profile Chrome với kịch bản thô được gán tự động"
    }


@app.post("/api/save-script")
async def save_script_from_claude(payload: ScriptPayload):
    """API dành riêng cho Tampermonkey Userscript trên Claude Web"""
    proj = database.create_project(
        title=payload.title,
        content=payload.content,
        status="1_cho_duyet",
        notes="Lưu tự động từ Claude Web (1-Click)"
    )
    return {"success": True, "id": proj["id"], "project": proj}


@app.get("/api/projects/{project_id}")
async def get_project_api(project_id: str):
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    return proj

@app.put("/api/projects/{project_id}")
async def update_project_api(project_id: str, data: dict = Body(...)):
    proj = database.update_project(project_id, **data)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    return proj

@app.put("/api/projects/{project_id}/toggle-published")
async def toggle_published_api(project_id: str):
    proj = database.toggle_published(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    return {"success": True, "is_published": proj.get("is_published", 0), "project": proj}

@app.put("/api/projects/{project_id}/toggle-thumbnail")
async def toggle_thumbnail_api(project_id: str):
    proj = database.toggle_thumbnail(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    return {"success": True, "has_thumbnail": proj.get("has_thumbnail", 0), "project": proj}

@app.delete("/api/projects/{project_id}")
async def delete_project_api(project_id: str):
    success = database.delete_project(project_id)
    return {"success": success}

@app.post("/api/projects/batch-delete")
async def batch_delete_projects_api(payload: BatchDeletePayload):
    count = database.batch_delete(payload.project_ids)
    return {"success": True, "deleted_count": count}

@app.post("/api/projects/{project_id}/generate-audio")
async def generate_audio_api(project_id: str, payload: AudioGenPayload):
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    t = task_queue.add_task("audio", project_id, {
        "voice": payload.voice,
        "rate": payload.rate,
        "pitch": payload.pitch
    })
    return {
        "success": True,
        "queued": True,
        "message": f"Đã thêm [{project_id}] vào Hàng Đợi Tạo Voice ngầm!",
        "task": t
    }

@app.post("/api/projects/{project_id}/create-capcut-draft")
async def create_capcut_draft_api(project_id: str, payload: CapCutDraftPayload):
    """Tự động tạo 1 Dự Án CapCut chuẩn 16:9 (YouTube) với video nền tự khớp"""
    proj = database.get_project(project_id)
    if not proj or not proj.get("audio_path"):
        raise HTTPException(status_code=400, detail="Chưa có file Audio. Vui lòng tạo Audio trước!")
    
    t = task_queue.add_task("capcut", project_id, {
        "theme": payload.theme or "nau_an"
    })
    return {
        "success": True,
        "queued": True,
        "message": f"Đã thêm [{project_id}] vào Hàng Đợi Tạo CapCut 16:9 ngầm!",
        "task": t
    }

@app.post("/api/projects/batch-create-capcut")
async def batch_create_capcut_api(payload: BatchCapCutPayload):
    """Tạo hàng loạt Dự Án CapCut 16:9 cho toàn bộ kịch bản đã chọn qua Hàng Đợi Ngầm"""
    tasks = task_queue.add_batch_tasks("capcut", payload.project_ids, {
        "theme": payload.theme or "nau_an"
    })
    return {
        "success": True,
        "queued": True,
        "created_count": len(tasks),
        "message": f"Đã thêm {len(tasks)} kịch bản vào Hàng Đợi Tạo CapCut ngầm!",
        "tasks": tasks
    }

@app.post("/api/projects/{project_id}/convert-to-tiktok")
async def convert_to_tiktok_api(project_id: str, payload: Optional[ConvertTikTokPayload] = None):
    """
    Tự động chuyển đổi video ngang (YouTube 16:9) sang video dọc (TikTok 9:16) siêu tốc
    bằng hiệu ứng nền mờ Cinematic (Blur Background) qua Hàng Đợi Ngầm!
    """
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    style = payload.style if payload else "blur"
    t = task_queue.add_task("tiktok", project_id, {"style": style})
    return {
        "success": True,
        "queued": True,
        "message": f"Đã thêm [{project_id}] vào Hàng Đợi Chuyển Đổi TikTok 9:16 ngầm!",
        "task": t
    }

@app.post("/api/projects/{project_id}/split-parts")
async def split_parts_api(project_id: str, payload: Optional[SplitPartsPayload] = None):
    """
    Cắt video dài (ví dụ 50 phút) thành chuỗi các tập ngắn Part 1, Part 2... cho TikTok (chỉ mất vài giây)
    """
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    part_dur = payload.part_duration_sec if payload else 180
    src_video = proj.get("video_tiktok_path") or proj.get("video_youtube_path") or proj.get("video_path")
    if not src_video or not os.path.exists(src_video):
        raise HTTPException(status_code=400, detail="Chưa có video để cắt tập!")
    
    pkg_dir = os.path.join(BASE_DIR, "outputs", project_id, "parts")
    os.makedirs(pkg_dir, exist_ok=True)
    
    try:
        parts = video_engine.split_video_into_parts(
            input_video_path=src_video,
            output_dir=pkg_dir,
            part_prefix=project_id,
            part_duration_sec=part_dur
        )
        return {
            "success": True,
            "parts_count": len(parts),
            "parts": parts,
            "message": f"Đã cắt thành công {len(parts)} tập ngắn vào thư mục outputs/{project_id}/parts/"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cắt tập: {str(e)}")

@app.post("/api/open-capcut")
async def open_capcut_app():
    """Mở ứng dụng CapCut PC"""
    opened = capcut_engine.launch_capcut_app()
    if opened:
        return {"success": True, "message": "Đã mở CapCut PC"}
    return {"success": False, "message": "Không tìm thấy CapCut.exe trong máy"}

@app.post("/api/projects/{project_id}/generate-thumb")
async def generate_thumb_api(project_id: str, payload: ThumbGenPayload):
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    pkg_dir = os.path.join(BASE_DIR, "outputs", project_id)
    os.makedirs(pkg_dir, exist_ok=True)
    pkg_thumb_path = os.path.join(pkg_dir, f"{project_id}_thumb.jpg")

    prompt = payload.prompt or f"Cinematic illustration for Vietnamese story: {proj['title']}"
    actual_path = thumbnail_engine.generate_thumbnail(
        prompt=prompt,
        output_path=pkg_thumb_path,
        aspect_ratio=payload.aspect_ratio or "9:16"
    )

    updated = database.update_project(
        project_id,
        has_thumbnail=1,
        thumbnail_path=actual_path
    )
    return {"success": True, "thumbnail_path": actual_path, "project": updated}

@app.get("/api/audio/{project_id}")
async def stream_audio(project_id: str):
    proj = database.get_project(project_id)
    if not proj or not proj.get("audio_path") or not os.path.exists(proj["audio_path"]):
        raise HTTPException(status_code=404, detail="File audio không tồn tại")
    media_type = "audio/wav" if proj["audio_path"].lower().endswith(".wav") else "audio/mpeg"
    return FileResponse(proj["audio_path"], media_type=media_type)

@app.get("/api/video/{project_id}")
async def stream_video(project_id: str):
    proj = database.get_project(project_id)
    target_path = proj.get("video_tiktok_path") or proj.get("video_youtube_path") or proj.get("video_path")
    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File video không tồn tại")
    return FileResponse(target_path, media_type="video/mp4")

@app.get("/api/thumb/{project_id}")
async def stream_thumb(project_id: str):
    proj = database.get_project(project_id)
    if not proj or not proj.get("thumbnail_path") or not os.path.exists(proj["thumbnail_path"]):
        raise HTTPException(status_code=404, detail="Ảnh thumbnail không tồn tại")
    return FileResponse(proj["thumbnail_path"], media_type="image/jpeg")

@app.post("/api/projects/{project_id}/open-package")
async def open_package_folder(project_id: str):
    """Mở đúng thư mục gói outputs/KBxxx của kịch bản trong Windows Explorer"""
    pkg_dir = os.path.join(BASE_DIR, "outputs", project_id)
    os.makedirs(pkg_dir, exist_ok=True)
    subprocess.Popen(f'explorer "{pkg_dir}"')
    return {"success": True, "opened": pkg_dir}

@app.post("/api/open-file-in-explorer")
async def open_file_in_explorer(payload: OpenFilePayload):
    """Mở Windows Explorer và tự động Highlight file được chọn"""
    target = os.path.abspath(payload.file_path)
    if os.path.exists(target):
        subprocess.Popen(f'explorer /select,"{target}"')
        return {"success": True, "opened": target}
    else:
        parent = os.path.dirname(target)
        if os.path.exists(parent):
            subprocess.Popen(f'explorer "{parent}"')
            return {"success": True, "opened": parent}
    raise HTTPException(status_code=404, detail="Không tìm thấy file hoặc thư mục")

@app.post("/api/open-folder")
async def open_folder(folder_name: str = Body(..., embed=True)):
    """Mở nhanh thư mục trực tiếp trong Windows Explorer"""
    valid_folders = {
        "root": BASE_DIR,
        "outputs": os.path.join(BASE_DIR, "outputs"),
        "backgrounds": os.path.join(BASE_DIR, "backgrounds"),
        "bg_nau_an_doc": os.path.join(BASE_DIR, "backgrounds", "nau_an", "doc"),
        "bg_nau_an_ngang": os.path.join(BASE_DIR, "backgrounds", "nau_an", "ngang"),
        "bg_handmade_doc": os.path.join(BASE_DIR, "backgrounds", "handmade", "doc"),
        "bg_handmade_ngang": os.path.join(BASE_DIR, "backgrounds", "handmade", "ngang"),
        "capcut_drafts": capcut_engine.CAPCUT_DRAFT_ROOT
    }
    target = valid_folders.get(folder_name, BASE_DIR)
    os.makedirs(target, exist_ok=True)
    subprocess.Popen(f'explorer "{target}"')
    return {"success": True, "opened": target}


@app.get("/claude_to_truyen.user.js")
async def serve_userscript():
    """Phục vụ file Tampermonkey script trực tiếp để cài đặt 1-click"""
    script_path = os.path.join(BASE_DIR, "tools", "claude_to_truyen.user.js")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy script")
    return FileResponse(script_path, media_type="application/javascript")

@app.post("/api/launch-chrome")
async def launch_chrome_profiles():
    """Khởi chạy 5 profile Chrome theo file bat"""
    bat_path = os.path.join(BASE_DIR, "tools", "launch_5_claude.bat")
    if os.path.exists(bat_path):
        subprocess.Popen(bat_path, shell=True)
        return {"success": True, "message": "Đã khởi chạy 5 cửa sổ Chrome"}
    return {"success": False, "message": "Không tìm thấy file bat"}

@app.on_event("startup")
async def startup_event():
    import voicestudio_service
    voicestudio_service.ensure_voicestudio_running()
    
    # Tự động mở trình duyệt web tới Web Dashboard
    import webbrowser, threading, time
    def _open_browser():
        time.sleep(1.0)
        try:
            webbrowser.open("http://localhost:8888")
        except Exception:
            pass
    threading.Thread(target=_open_browser, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)
