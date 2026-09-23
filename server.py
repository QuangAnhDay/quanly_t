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

# Khởi tạo toàn bộ thư mục cần thiết
capcut_engine.init_theme_folders()
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)

# Khởi tạo DB
database.init_db()

app = FastAPI(title="Xưởng Sản Xuất Video Audio - Truyện Automation")

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

class BatchDeletePayload(BaseModel):
    project_ids: List[str]

class OpenFilePayload(BaseModel):
    file_path: str

class ConvertTikTokPayload(BaseModel):
    style: Optional[str] = "blur"

class SplitPartsPayload(BaseModel):
    part_duration_sec: Optional[int] = 180

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
    
    pkg_dir = os.path.join(BASE_DIR, "outputs", project_id)
    os.makedirs(pkg_dir, exist_ok=True)
    pkg_audio_path = os.path.join(pkg_dir, f"{project_id}_voice.mp3")

    audio_path = await audio_engine.generate_speech(
        text=proj["content"],
        output_filename=f"{project_id}.mp3",
        voice=payload.voice or proj.get("voice") or "vi-VN-HoaiMyNeural",
        rate=payload.rate or "+0%",
        pitch=payload.pitch or "+0Hz"
    )
    
    import shutil
    try:
        shutil.copy2(audio_path, pkg_audio_path)
        actual_path = pkg_audio_path
    except Exception:
        actual_path = audio_path
    
    updated = database.update_project(
        project_id,
        audio_path=actual_path,
        voice=payload.voice,
        rate=payload.rate,
        pitch=payload.pitch,
        status="3_da_co_audio"
    )
    return {"success": True, "audio_path": actual_path, "project": updated}

@app.post("/api/projects/{project_id}/create-capcut-draft")
async def create_capcut_draft_api(project_id: str, payload: CapCutDraftPayload):
    """Tự động tạo 1 Dự Án CapCut chuẩn 16:9 (YouTube) với video nền tự khớp"""
    proj = database.get_project(project_id)
    if not proj or not proj.get("audio_path"):
        raise HTTPException(status_code=400, detail="Chưa có file Audio. Vui lòng tạo Audio trước!")
    
    audio_path = proj["audio_path"]
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy file audio tại {audio_path}")

    theme = payload.theme or "nau_an"
    try:
        draft_res = capcut_engine.create_capcut_draft(
            project_id=project_id,
            title=proj["title"],
            audio_path=audio_path,
            theme=theme
        )
        theme_names = {"nau_an": "Nấu ăn", "handmade": "Handmade"}
        theme_vn = theme_names.get(theme, theme)
        
        draft_name = draft_res["draft_name"]
        notes = f"CapCut ({theme_vn}): {draft_name}"
        
        updated = database.update_project(
            project_id,
            capcut_draft_youtube=draft_name,
            notes=notes,
            status="4_da_render_video"
        )
        
        return {
            "success": True,
            "message": f"Đã tạo xong Project CapCut: {draft_name} ({draft_res['clips_count']} clip nền)!",
            "draft_info": draft_res,
            "project": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/batch-create-capcut")
async def batch_create_capcut_api(payload: BatchCapCutPayload):
    """Tạo hàng loạt Dự Án CapCut 16:9 cho toàn bộ kịch bản đã chọn"""
    theme = payload.theme or "nau_an"
    theme_names = {"nau_an": "Nấu ăn", "handmade": "Handmade"}
    theme_vn = theme_names.get(theme, theme)
    
    results = []
    success_count = 0
    errors = []

    for pid in payload.project_ids:
        proj = database.get_project(pid)
        if not proj or not proj.get("audio_path") or not os.path.exists(proj["audio_path"]):
            errors.append(f"{pid}: Chưa có file audio")
            continue
        try:
            draft_res = capcut_engine.create_capcut_draft(
                project_id=pid,
                title=proj["title"],
                audio_path=proj["audio_path"],
                theme=theme
            )
            notes = f"CapCut ({theme_vn}): {draft_res['draft_name']}"
            database.update_project(
                pid,
                capcut_draft_youtube=draft_res["draft_name"],
                notes=notes,
                status="4_da_render_video"
            )
            results.append({"id": pid, "draft_name": draft_res["draft_name"], "clips": draft_res["clips_count"]})
            success_count += 1
        except Exception as e:
            errors.append(f"{pid}: {str(e)}")

    return {
        "success": True,
        "created_count": success_count,
        "results": results,
        "errors": errors
    }

@app.post("/api/projects/{project_id}/convert-to-tiktok")
async def convert_to_tiktok_api(project_id: str, payload: Optional[ConvertTikTokPayload] = None):
    """
    Tự động chuyển đổi video ngang (YouTube 16:9) sang video dọc (TikTok 9:16) siêu tốc
    bằng hiệu ứng nền mờ Cinematic (Blur Background) không cần render lại CapCut lần 2!
    """
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    style = payload.style if payload else "blur"
    
    # Tìm file video nguồn 16:9
    src_video = proj.get("video_youtube_path") or proj.get("video_path")
    if not src_video or not os.path.exists(src_video):
        pkg_dir = os.path.join(BASE_DIR, "outputs", project_id)
        if os.path.exists(pkg_dir):
            for f in os.listdir(pkg_dir):
                if f.lower().endswith((".mp4", ".mov")) and "tiktok" not in f.lower() and "doc" not in f.lower():
                    src_video = os.path.join(pkg_dir, f)
                    break
    
    if not src_video or not os.path.exists(src_video):
        raise HTTPException(status_code=400, detail="Chưa có video ngang (YouTube) để chuyển đổi! Vui lòng xuất video YouTube trước.")

    pkg_dir = os.path.join(BASE_DIR, "outputs", project_id)
    os.makedirs(pkg_dir, exist_ok=True)
    out_tiktok_path = os.path.join(pkg_dir, f"{project_id}_tiktok.mp4")

    try:
        video_engine.convert_16x9_to_9x16(src_video, out_tiktok_path, style=style)
        updated = database.update_project(
            project_id,
            video_tiktok_path=out_tiktok_path,
            status="5_hoan_thanh"
        )
        return {
            "success": True,
            "message": "Đã chuyển đổi thành công sang bản dọc TikTok 9:16 (Nền mờ Cinematic)!",
            "video_tiktok_path": out_tiktok_path,
            "project": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi chuyển đổi video: {str(e)}")

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
    output_filename = f"{project_id}.jpg"
    thumb_path = thumbnail_engine.generate_thumbnail(
        prompt=prompt,
        output_filename=output_filename,
        aspect_ratio=payload.aspect_ratio or "9:16"
    )
    
    import shutil
    try:
        shutil.copy2(thumb_path, pkg_thumb_path)
        actual_path = pkg_thumb_path
    except Exception:
        actual_path = thumb_path

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
        "scripts": os.path.join(BASE_DIR, "1_scripts"),
        "audios": os.path.join(BASE_DIR, "2_audio_input"),
        "videos": os.path.join(BASE_DIR, "3_video_output"),
        "thumbnails": os.path.join(BASE_DIR, "4_thumbnails"),
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

@app.post("/api/launch-chrome")
async def launch_chrome_profiles():
    """Khởi chạy 5 profile Chrome theo file bat"""
    bat_path = os.path.join(BASE_DIR, "tools", "launch_5_claude.bat")
    if os.path.exists(bat_path):
        subprocess.Popen(bat_path, shell=True)
        return {"success": True, "message": "Đã khởi chạy 5 cửa sổ Chrome"}
    return {"success": False, "message": "Không tìm thấy file bat"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)
