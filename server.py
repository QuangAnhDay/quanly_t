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
    """Tự động kiểm tra các thư mục đĩa để đồng bộ trạng thái Audio, Video Đa Kênh và Thumbnail"""
    audio_dir = os.path.join(BASE_DIR, "2_audio_input")
    video_dir = os.path.join(BASE_DIR, "3_video_output")
    tiktok_dir = os.path.join(video_dir, "tiktok")
    youtube_dir = os.path.join(video_dir, "youtube")
    thumb_dir = os.path.join(BASE_DIR, "4_thumbnails")
    
    projects = database.get_all_projects()
    for p in projects:
        pid = p["id"]
        updates = {}
        
        # 1. Kiểm tra file audio
        if not p.get("audio_path") or not os.path.exists(p["audio_path"]):
            for ext in [".wav", ".mp3", ".m4a"]:
                cand = os.path.join(audio_dir, f"{pid}{ext}")
                if os.path.exists(cand):
                    updates["audio_path"] = cand
                    if p["status"] in ["1_cho_duyet", "2_cho_voice"]:
                        updates["status"] = "3_da_co_audio"
                    break
        
        # 2. Kiểm tra Video TikTok
        if not p.get("video_tiktok_path") or not os.path.exists(p["video_tiktok_path"]):
            for ext in [".mp4", ".mov"]:
                cand = os.path.join(tiktok_dir, f"{pid}{ext}")
                if not os.path.exists(cand):
                    cand = os.path.join(tiktok_dir, f"{pid}_tiktok{ext}")
                if os.path.exists(cand):
                    updates["video_tiktok_path"] = cand
                    break
                    
        # 3. Kiểm tra Video YouTube
        if not p.get("video_youtube_path") or not os.path.exists(p["video_youtube_path"]):
            for ext in [".mp4", ".mov"]:
                cand = os.path.join(youtube_dir, f"{pid}{ext}")
                if not os.path.exists(cand):
                    cand = os.path.join(youtube_dir, f"{pid}_youtube{ext}")
                if os.path.exists(cand):
                    updates["video_youtube_path"] = cand
                    break
                    
        # 4. Kiểm tra Video chung
        if not p.get("video_path") or not os.path.exists(p["video_path"]):
            cand = os.path.join(video_dir, f"{pid}.mp4")
            if os.path.exists(cand):
                updates["video_path"] = cand
            elif updates.get("video_tiktok_path"):
                updates["video_path"] = updates["video_tiktok_path"]
            elif updates.get("video_youtube_path"):
                updates["video_path"] = updates["video_youtube_path"]

        # Nếu có video đã xuất thì cập nhật hoàn thành
        if (updates.get("video_tiktok_path") or updates.get("video_youtube_path") or updates.get("video_path")) and p["status"] != "5_hoan_thanh":
            updates["status"] = "5_hoan_thanh"

        # 5. Kiểm tra Thumbnail
        if not p.get("has_thumbnail") or not p.get("thumbnail_path") or not os.path.exists(p.get("thumbnail_path", "")):
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                cand = os.path.join(thumb_dir, f"{pid}{ext}")
                if os.path.exists(cand):
                    updates["has_thumbnail"] = 1
                    updates["thumbnail_path"] = cand
                    break

        if updates:
            database.update_project(pid, **updates)

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
    
    output_filename = f"{project_id}.mp3"
    audio_path = await audio_engine.generate_speech(
        text=proj["content"],
        output_filename=output_filename,
        voice=payload.voice or proj.get("voice") or "vi-VN-HoaiMyNeural",
        rate=payload.rate or "+0%",
        pitch=payload.pitch or "+0Hz"
    )
    
    updated = database.update_project(
        project_id,
        audio_path=audio_path,
        voice=payload.voice,
        rate=payload.rate,
        pitch=payload.pitch,
        status="3_da_co_audio"
    )
    return {"success": True, "audio_path": audio_path, "project": updated}

@app.post("/api/projects/{project_id}/create-capcut-draft")
async def create_capcut_draft_api(project_id: str, payload: CapCutDraftPayload):
    """Tự động tạo ĐỒNG THỜI 2 Dự Án CapCut (TikTok 9:16 và YouTube 16:9) với video nền tự khớp"""
    proj = database.get_project(project_id)
    if not proj or not proj.get("audio_path"):
        raise HTTPException(status_code=400, detail="Chưa có file Audio. Vui lòng tạo Audio trước!")
    
    audio_path = proj["audio_path"]
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy file audio tại {audio_path}")

    theme = payload.theme or "nau_an"
    try:
        draft_res = capcut_engine.create_dual_capcut_drafts(
            project_id=project_id,
            title=proj["title"],
            audio_path=audio_path,
            theme=theme
        )
        theme_names = {"nau_an": "Nấu ăn", "handmade": "Handmade"}
        theme_vn = theme_names.get(theme, theme)
        
        tiktok_name = draft_res["tiktok"]["draft_name"]
        youtube_name = draft_res["youtube"]["draft_name"]
        notes = f"CapCut ({theme_vn}): TikTok & YouTube"
        
        updated = database.update_project(
            project_id,
            capcut_draft_tiktok=tiktok_name,
            capcut_draft_youtube=youtube_name,
            notes=notes,
            status="4_da_render_video"
        )
        
        return {
            "success": True,
            "message": f"Đã tạo xong 2 Dự Án CapCut: [TikTok 9:16 ({draft_res['tiktok']['clips_count']} clip)] & [YouTube 16:9 ({draft_res['youtube']['clips_count']} clip)]",
            "draft_info": draft_res,
            "project": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/batch-create-capcut")
async def batch_create_capcut_api(payload: BatchCapCutPayload):
    """Tạo hàng loạt 2 Dự Án CapCut (TikTok & YouTube) cho toàn bộ kịch bản đã chọn"""
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
            draft_res = capcut_engine.create_dual_capcut_drafts(
                project_id=pid,
                title=proj["title"],
                audio_path=proj["audio_path"],
                theme=theme
            )
            notes = f"CapCut ({theme_vn}): TikTok & YouTube"
            database.update_project(
                pid,
                capcut_draft_tiktok=draft_res["tiktok"]["draft_name"],
                capcut_draft_youtube=draft_res["youtube"]["draft_name"],
                notes=notes,
                status="4_da_render_video"
            )
            results.append({"id": pid, "tiktok": draft_res["tiktok"]["draft_name"], "youtube": draft_res["youtube"]["draft_name"]})
            success_count += 1
        except Exception as e:
            errors.append(f"{pid}: {str(e)}")

    return {
        "success": True,
        "created_count": success_count,
        "results": results,
        "errors": errors
    }

@app.post("/api/open-capcut")
async def open_capcut_app():
    """Mở ứng dụng CapCut PC"""
    opened = capcut_engine.launch_capcut_app()
    if opened:
        return {"success": True, "message": "Đã mở CapCut PC"}
    return {"success": False, "message": "Không tìm thấy CapCut.exe trong máy"}

@app.post("/api/projects/{project_id}/render-video")
async def render_video_api(project_id: str, payload: RenderVideoPayload):
    proj = database.get_project(project_id)
    if not proj or not proj.get("audio_path"):
        raise HTTPException(status_code=400, detail="Chưa có file Audio. Vui lòng tạo Audio trước!")
    
    audio_path = proj["audio_path"]
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy file audio tại {audio_path}")
        
    output_filename = f"{project_id}.mp4"
    video_path = video_engine.render_video(
        audio_path=audio_path,
        output_filename=output_filename,
        title=proj["title"],
        aspect_ratio=payload.aspect_ratio or "9:16"
    )
    
    updated = database.update_project(
        project_id,
        video_path=video_path,
        video_tiktok_path=video_path,
        status="4_da_render_video"
    )
    return {"success": True, "video_path": video_path, "project": updated}

@app.post("/api/projects/{project_id}/generate-thumb")
async def generate_thumb_api(project_id: str, payload: ThumbGenPayload):
    proj = database.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản")
    
    prompt = payload.prompt or f"Cinematic illustration for Vietnamese story: {proj['title']}"
    output_filename = f"{project_id}.jpg"
    thumb_path = thumbnail_engine.generate_thumbnail(
        prompt=prompt,
        output_filename=output_filename,
        aspect_ratio=payload.aspect_ratio or "9:16"
    )
    
    updated = database.update_project(
        project_id,
        has_thumbnail=1,
        thumbnail_path=thumb_path
    )
    return {"success": True, "thumbnail_path": thumb_path, "project": updated}

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

@app.post("/api/open-file-in-explorer")
async def open_file_in_explorer(payload: OpenFilePayload):
    """Mở Windows Explorer và tự động Highlight file được chọn"""
    target = os.path.abspath(payload.file_path)
    if os.path.exists(target):
        subprocess.Popen(f'explorer /select,"{target}"')
        return {"success": True, "opened": target}
    else:
        # Nếu file chưa có thì mở thư mục cha
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
        "scripts": os.path.join(BASE_DIR, "1_scripts"),
        "audios": os.path.join(BASE_DIR, "2_audio_input"),
        "videos": os.path.join(BASE_DIR, "3_video_output"),
        "tiktok_videos": os.path.join(BASE_DIR, "3_video_output", "tiktok"),
        "youtube_videos": os.path.join(BASE_DIR, "3_video_output", "youtube"),
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
