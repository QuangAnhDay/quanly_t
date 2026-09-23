import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "truyen.db")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        raw_content TEXT,
        thumb_prompt TEXT,
        status TEXT NOT NULL DEFAULT '1_cho_duyet',
        voice TEXT DEFAULT 'vi-VN-HoaiMyNeural',
        rate TEXT DEFAULT '+0%',
        pitch TEXT DEFAULT '+0Hz',
        audio_path TEXT,
        video_path TEXT,
        video_tiktok_path TEXT,
        video_youtube_path TEXT,
        capcut_draft_tiktok TEXT,
        capcut_draft_youtube TEXT,
        has_thumbnail INTEGER DEFAULT 0,
        thumbnail_path TEXT,
        package_dir TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        notes TEXT,
        is_published INTEGER DEFAULT 0
    )
    """)
    
    # Kiểm tra migration cho các cột mới
    cursor.execute("PRAGMA table_info(projects)")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations = [
        ("is_published", "INTEGER DEFAULT 0"),
        ("video_tiktok_path", "TEXT"),
        ("video_youtube_path", "TEXT"),
        ("capcut_draft_tiktok", "TEXT"),
        ("capcut_draft_youtube", "TEXT"),
        ("has_thumbnail", "INTEGER DEFAULT 0"),
        ("package_dir", "TEXT"),
        ("raw_content", "TEXT"),
        ("thumb_prompt", "TEXT"),
    ]
    
    for col_name, col_type in migrations:
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Migration notice ({col_name}): {e}")
        
    conn.commit()
    conn.close()

def get_next_kb_id() -> str:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects")
    rows = cursor.fetchall()
    conn.close()

    max_num = 0
    for (pid,) in rows:
        match = re.match(r"^KB(\d+)$", pid, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f"KB{max_num + 1:03d}"

def get_package_dir(kb_id: str) -> str:
    """Tạo và trả về đường dẫn thư mục trọn gói cho kịch bản outputs/KBxxx/"""
    pkg_dir = os.path.join(OUTPUTS_DIR, kb_id)
    os.makedirs(pkg_dir, exist_ok=True)
    return pkg_dir

def create_project(
    title: str,
    content: str,
    status: str = "1_cho_duyet",
    voice: str = "vi-VN-HoaiMyNeural",
    notes: str = "",
    raw_content: str = "",
    thumb_prompt: str = ""
) -> Dict[str, Any]:
    init_db()
    kb_id = get_next_kb_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pkg_dir = get_package_dir(kb_id)

    # Lưu file text kịch bản trực tiếp vào gói outputs/KBxxx/KBxxx_script.txt
    pkg_script_file = os.path.join(pkg_dir, f"{kb_id}_script.txt")
    with open(pkg_script_file, "w", encoding="utf-8") as f:
        f.write(f"Tiêu đề: {title}\n")
        f.write(f"Mã kịch bản: {kb_id}\n")
        f.write(f"Ngày tạo: {now}\n")
        if raw_content:
            f.write(f"Kịch bản thô ban đầu:\n{raw_content}\n")
            f.write("-" * 40 + "\n")
        f.write("="*40 + "\n\n")
        f.write(content or raw_content)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO projects (
        id, title, content, raw_content, thumb_prompt, status, voice, rate, pitch, 
        audio_path, video_path, video_tiktok_path, video_youtube_path,
        capcut_draft_tiktok, capcut_draft_youtube, has_thumbnail, thumbnail_path,
        package_dir, created_at, updated_at, notes, is_published
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, '+0%', '+0Hz', NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, ?, ?, ?, ?, 0)
    """, (kb_id, title, content, raw_content, thumb_prompt, status, voice, pkg_dir, now, now, notes))
    conn.commit()
    conn.close()

    return get_project(kb_id)

def create_raw_project(raw_content: str, title: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
    """Tạo một kịch bản thô (chờ AI hoàn thiện)"""
    first_line = raw_content.strip().split("\n")[0][:40] if raw_content.strip() else "Kịch bản thô"
    auto_title = title or f"Bản thô: {first_line}..."
    return create_project(
        title=auto_title,
        content="",
        raw_content=raw_content,
        status="0_ban_tho",
        notes=notes or "Kịch bản thô (Chờ Claude xử lý 2 Skill)"
    )

def batch_create_raw_projects(raw_list: List[str]) -> List[Dict[str, Any]]:
    """Tạo hàng loạt kịch bản thô cùng lúc"""
    results = []
    for raw in raw_list:
        clean = raw.strip()
        if clean:
            p = create_raw_project(clean)
            results.append(p)
    return results

def get_pending_raw_projects() -> List[Dict[str, Any]]:
    """Lấy danh sách các kịch bản thô chưa được AI xử lý"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE status = '0_ban_tho' ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def complete_raw_project(project_id: str, title: str, content: str, thumb_prompt: str = "", notes: str = "") -> Optional[Dict[str, Any]]:
    """Cập nhật kịch bản thô sau khi Claude chạy xong 2 Skill"""
    p = get_project(project_id)
    if not p:
        return None
    
    pkg_dir = get_package_dir(project_id)
    pkg_script_file = os.path.join(pkg_dir, f"{project_id}_script.txt")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(pkg_script_file, "w", encoding="utf-8") as f:
        f.write(f"Tiêu đề: {title}\n")
        f.write(f"Mã kịch bản: {project_id}\n")
        f.write(f"Ngày cập nhật: {now}\n")
        if p.get("raw_content"):
            f.write(f"Kịch bản thô gốc:\n{p['raw_content']}\n")
            f.write("-" * 40 + "\n")
        if thumb_prompt:
            f.write(f"Gợi ý Thumbnail Prompt:\n{thumb_prompt}\n")
            f.write("-" * 40 + "\n")
        f.write("="*40 + "\n\n")
        f.write(content)

    updated_notes = notes or f"AI Claude hoàn thiện lúc {now}"
    return update_project(
        project_id,
        title=title,
        content=content,
        thumb_prompt=thumb_prompt,
        status="1_cho_duyet",
        notes=updated_notes
    )


def get_all_projects() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_project(project_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    init_db()
    if not kwargs:
        return get_project(project_id)

    kwargs["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(project_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_project(project_id)

def toggle_published(project_id: str) -> Optional[Dict[str, Any]]:
    """Đảo trạng thái đã đăng / chưa đăng của kịch bản"""
    p = get_project(project_id)
    if not p:
        return None
    new_val = 0 if p.get("is_published", 0) else 1
    return update_project(project_id, is_published=new_val)

def toggle_thumbnail(project_id: str) -> Optional[Dict[str, Any]]:
    """Đảo trạng thái đã có thumbnail hay chưa"""
    p = get_project(project_id)
    if not p:
        return None
    new_val = 0 if p.get("has_thumbnail", 0) else 1
    return update_project(project_id, has_thumbnail=new_val)

import shutil
import glob

CAPCUT_DRAFT_ROOT = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")

def clean_project_files(project_id: str):
    """
    Xóa sạch toàn bộ dữ liệu của kịch bản:
    - Gói thư mục duy nhất outputs/KBxxx/
    - Draft dự án trong CapCut PC
    """
    if not project_id:
        return
    
    # 1. Xóa gói outputs/KBxxx/
    pkg_dir = os.path.join(OUTPUTS_DIR, project_id)
    if os.path.exists(pkg_dir):
        try:
            shutil.rmtree(pkg_dir, ignore_errors=True)
        except Exception as e:
            print(f"[Delete] Lỗi xóa thư mục {pkg_dir}: {e}")

    # 2. Xóa Dự án Draft trong CapCut PC nếu có
    if os.path.exists(CAPCUT_DRAFT_ROOT):
        for d in glob.glob(os.path.join(CAPCUT_DRAFT_ROOT, f"{project_id}_*")):
            if os.path.isdir(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass

def delete_project(project_id: str) -> bool:
    clean_project_files(project_id)
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def batch_delete(project_ids: List[str]) -> int:
    """Xóa hàng loạt kịch bản và toàn bộ file liên quan theo danh sách ID"""
    if not project_ids:
        return 0
    for pid in project_ids:
        clean_project_files(pid)
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(project_ids))
    cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count


def sync_project_files(pid: str) -> Optional[Dict[str, Any]]:
    """
    Quét thực tế duy nhất gói outputs/KBxxx và đồng bộ chuẩn xác trạng thái trong DB
    """
    p = get_project(pid)
    if not p:
        return None
    
    pkg_dir = os.path.join(OUTPUTS_DIR, pid)
    
    found_audio = None
    found_tt = None
    found_yt = None
    found_th = None
    
    if os.path.exists(pkg_dir):
        for f in os.listdir(pkg_dir):
            fn_lower = f.lower()
            full_p = os.path.join(pkg_dir, f)
            if os.path.isdir(full_p):
                continue
                
            # 1. Voice Audio
            if fn_lower.endswith((".wav", ".mp3", ".m4a")):
                if not found_audio:
                    found_audio = full_p
                    
            # 2. Video
            elif fn_lower.endswith((".mp4", ".mov", ".mkv")):
                if "tiktok" in fn_lower or "doc" in fn_lower:
                    found_tt = full_p
                elif "youtube" in fn_lower or "ngang" in fn_lower or "yt" in fn_lower:
                    found_yt = full_p
                else:
                    # Nếu file mp4 chung chưa phân loại, mặc định coi là video YouTube (16:9)
                    if not found_yt:
                        found_yt = full_p
                        
            # 3. Thumbnail
            elif fn_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                if not found_th:
                    found_th = full_p

    updates = {}
    if p.get("audio_path") != found_audio:
        updates["audio_path"] = found_audio
        
    if p.get("video_tiktok_path") != found_tt:
        updates["video_tiktok_path"] = found_tt
        
    if p.get("video_youtube_path") != found_yt:
        updates["video_youtube_path"] = found_yt
        
    main_video = found_yt or found_tt
    if p.get("video_path") != main_video:
        updates["video_path"] = main_video
        
    has_thumb_val = 1 if (found_th or p.get("has_thumbnail") == 1) else 0
    if p.get("has_thumbnail") != has_thumb_val or p.get("thumbnail_path") != found_th:
        updates["has_thumbnail"] = has_thumb_val
        updates["thumbnail_path"] = found_th

    # Cập nhật status logic
    current_status = p.get("status", "1_cho_duyet")
    new_status = current_status
    if main_video:
        new_status = "5_hoan_thanh"
    elif p.get("capcut_draft_youtube") or p.get("capcut_draft_tiktok") or (p.get("notes") and "CapCut" in p.get("notes", "")):
        new_status = "4_dang_dung_video"
    elif found_audio:
        new_status = "3_da_co_audio"
    else:
        if current_status in ["3_da_co_audio", "4_dang_dung_video", "5_hoan_thanh"]:
            new_status = "1_cho_duyet"
            
    if new_status != current_status:
        updates["status"] = new_status

    if updates:
        return update_project(pid, **updates)
    return p

def sync_all_projects() -> List[Dict[str, Any]]:
    """Đồng bộ thực tế tất cả các kịch bản với thư mục outputs/"""
    projects = get_all_projects()
    for p in projects:
        sync_project_files(p["id"])
    return get_all_projects()

