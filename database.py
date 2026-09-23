import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "truyen.db")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
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

def create_project(title: str, content: str, status: str = "1_cho_duyet", voice: str = "vi-VN-HoaiMyNeural", notes: str = "") -> Dict[str, Any]:
    init_db()
    kb_id = get_next_kb_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Lưu file text dự phòng vào 1_scripts/KBxxx.txt
    scripts_dir = os.path.join(os.path.dirname(__file__), "1_scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    clean_sub_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:30]
    script_file = os.path.join(scripts_dir, f"{kb_id}_{clean_sub_title}.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"Tiêu đề: {title}\n")
        f.write(f"Mã kịch bản: {kb_id}\n")
        f.write(f"Ngày tạo: {now}\n")
        f.write("="*40 + "\n\n")
        f.write(content)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO projects (
        id, title, content, status, voice, rate, pitch, 
        audio_path, video_path, video_tiktok_path, video_youtube_path,
        capcut_draft_tiktok, capcut_draft_youtube, has_thumbnail, thumbnail_path,
        created_at, updated_at, notes, is_published
    )
    VALUES (?, ?, ?, ?, ?, '+0%', '+0Hz', NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, ?, ?, ?, 0)
    """, (kb_id, title, content, status, voice, now, now, notes))
    conn.commit()
    conn.close()

    return get_project(kb_id)

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

def delete_project(project_id: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def batch_delete(project_ids: List[str]) -> int:
    """Xóa hàng loạt kịch bản theo danh sách ID"""
    init_db()
    if not project_ids:
        return 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(project_ids))
    cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count
