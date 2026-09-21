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
        thumbnail_path TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        notes TEXT
    )
    """)
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

    # Also save raw text file to 1_scripts/KBxxx.txt for easy manual reading/backup
    scripts_dir = os.path.join(os.path.dirname(__file__), "1_scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    script_file = os.path.join(scripts_dir, f"{kb_id}_{re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:30]}.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"Tiêu đề: {title}\n")
        f.write(f"Mã kịch bản: {kb_id}\n")
        f.write(f"Ngày tạo: {now}\n")
        f.write("="*40 + "\n\n")
        f.write(content)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO projects (id, title, content, status, voice, rate, pitch, audio_path, video_path, thumbnail_path, created_at, updated_at, notes)
    VALUES (?, ?, ?, ?, ?, '+0%', '+0Hz', NULL, NULL, NULL, ?, ?, ?)
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

def delete_project(project_id: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0
