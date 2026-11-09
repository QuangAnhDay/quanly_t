import sqlite3
import os
import re
import shutil
import glob
from datetime import datetime
from typing import List, Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "truyen.db")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
TIKTOK_READY_DIR = os.path.join(OUTPUTS_DIR, "tiktok_ready")
YOUTUBE_DIR = os.path.join(OUTPUTS_DIR, "youtube")
ARCHIVES_DIR = os.path.join(OUTPUTS_DIR, "archives")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(TIKTOK_READY_DIR, exist_ok=True)
    os.makedirs(YOUTUBE_DIR, exist_ok=True)
    os.makedirs(ARCHIVES_DIR, exist_ok=True)
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
        ("bg_video", "TEXT"),
        ("bg_theme", "TEXT"),
        ("theme", "TEXT DEFAULT 'nau_an'"),
        ("affiliate_comment", "TEXT"),
        ("affiliate_link", "TEXT"),
        ("ytb_episode", "INTEGER"),
        ("tiktok_posted", "INTEGER DEFAULT 0"),
        ("tiktok_posted_at", "TEXT"),
        ("tiktok_account", "TEXT"),
        ("tiktok_video_id", "TEXT"),
        ("genre", "TEXT"),
        ("target_skill", "TEXT"),
        ("tiktok_full_duration", "INTEGER DEFAULT 0"),
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
    """Tạo và trả về đường dẫn thư mục gói cho YouTube outputs/youtube/KBxxx/"""
    pkg_dir = os.path.join(YOUTUBE_DIR, kb_id)
    os.makedirs(pkg_dir, exist_ok=True)
    return pkg_dir

def get_archive_dir(kb_id: str) -> str:
    """Tạo và trả về đường dẫn thư mục lưu trữ tài nguyên thô outputs/archives/KBxxx/"""
    arch_dir = os.path.join(ARCHIVES_DIR, kb_id)
    os.makedirs(arch_dir, exist_ok=True)
    return arch_dir

def sync_tiktok_episode_file(project_id: str, episode: Optional[int] = None) -> Optional[str]:
    """
    Đồng bộ file text chứa số tập cho video TikTok trong outputs/tiktok_ready/
    - Nếu có video TikTok và có số tập hợp lệ: Ghi/ghi đè file [tên_video].txt với nội dung là số tập.
    - Nếu số tập là None hoặc rỗng: Xóa file .txt tương ứng nếu có để bot TikTok không quét nhầm.
    """
    os.makedirs(TIKTOK_READY_DIR, exist_ok=True)
    tt_base = None
    for f in os.listdir(TIKTOK_READY_DIR):
        fl = f.lower()
        if fl.startswith(project_id.lower()) and fl.endswith(('.mp4', '.mov', '.mkv')):
            tt_base = os.path.splitext(f)[0]
            break
            
    if not tt_base:
        tt_base = f"{project_id}_tiktok"
        
    txt_path = os.path.join(TIKTOK_READY_DIR, f"{tt_base}.txt")
    
    if episode is not None and str(episode).strip():
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(str(episode).strip())
        return txt_path
    else:
        if os.path.exists(txt_path):
            try:
                os.remove(txt_path)
            except Exception:
                pass
        return None


def detect_story_genre_and_skill(text: str) -> tuple:
    """Tự động nhận diện thể loại và Skill tương ứng từ nội dung kịch bản"""
    if not text:
        return "chung", "/kichban-audio-bancungphong"
        
    # 1. Quét thẻ metadata nếu có: [THE_LOAI: xxx | SKILL: yyy]
    m_tag = re.search(r'\[(?:THE_LOAI|GENRE):?\s*([^|\]]+)(?:\|\s*SKILL:?\s*([^\]]+))?\]', text, re.IGNORECASE)
    if m_tag:
        g = m_tag.group(1).strip()
        s = m_tag.group(2).strip() if m_tag.group(2) else ""
        if s:
            return g, s
        skill_map = {
            "bancungphong": "/kichban-audio-bancungphong",
            "chi_em": "/kichban-audio-chiem",
            "hoakhoi": "/kichban-audio-hoakhoi",
            "hoc_duong": "/kichban-audio-hoakhoi",
            "giadinh_vochong": "/kichban-audio-giadinh-vochong",
            "hohang": "/kichban-audio-hohang",
            "congso": "/kichban-audio-congso",
            "nu_chinh": "/kichban-nu-chinh",
            "drama": "/drama"
        }
        return g, skill_map.get(g, "/kichban-audio-bancungphong")

    # 2. Quét từ khóa tự động
    t_low = text.lower()
    if any(k in t_low for k in ["bạn cùng phòng", "ký túc xá", "ktx", "giường tầng", "bạn chung phòng"]):
        return "bancungphong", "/kichban-audio-bancungphong"
    if any(k in t_low for k in ["chị họ", "chị em", "em gái", "chị gái", "mẹ thiên vị", "bà ngoại", "hồi môn", "nhường em"]):
        return "chi_em", "/kichban-audio-chiem"
    if any(k in t_low for k in ["họ hàng", "dì hai", "bác cả", "chú thím", "tiệc cưới", "bánh hỷ"]):
        return "hohang", "/kichban-audio-hohang"
    if any(k in t_low for k in ["hoa khôi", "lớp trưởng", "học bổng", "đề thi", "bảo tống", "học sinh giỏi", "cao khảo"]):
        return "hoakhoi", "/kichban-audio-hoakhoi"
    if any(k in t_low for k in ["chồng", "mẹ chồng", "ly hôn", "ngoại tình", "tiểu tam", "sếp lớn", "kết hôn chớp nhoáng"]):
        return "giadinh_vochong", "/kichban-audio-giadinh-vochong"
    if any(k in t_low for k in ["công sở", "đồng nghiệp", "thực tập sinh", "sếp", "bản vẽ", "sa thải", "dự án"]):
        return "congso", "/kichban-audio-congso"
    if any(k in t_low for k in ["đòi quà", "chia tay", "đào mỏ", "sao kê", "văn phòng", "tàn dư"]):
        return "nu_chinh", "/kichban-nu-chinh"
        
    return "chung", "/kichban-audio-bancungphong"

def create_project(
    title: str,
    content: str,
    status: str = "1_cho_duyet",
    voice: str = "voicestudio:dda59bfa",
    notes: str = "",
    raw_content: str = "",
    thumb_prompt: str = "",
    theme: str = "nau_an",
    genre: str = "",
    target_skill: str = "",
    tiktok_full_duration: int = 0
) -> Dict[str, Any]:
    init_db()
    kb_id = get_next_kb_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pkg_dir = get_package_dir(kb_id)

    # Lưu file text kịch bản vào thư mục lưu trữ outputs/archives/KBxxx/
    arch_dir = get_archive_dir(kb_id)
    pkg_script_file = os.path.join(arch_dir, f"{kb_id}_script.txt")
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
        package_dir, created_at, updated_at, notes, is_published, theme, bg_theme,
        genre, target_skill, tiktok_full_duration
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, '+0%', '+0Hz', NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
    """, (kb_id, title, content, raw_content, thumb_prompt, status, voice, pkg_dir, now, now, notes, theme, theme, genre, target_skill, tiktok_full_duration))
    conn.commit()
    conn.close()

    return get_project(kb_id)

def create_raw_project(
    raw_content: str,
    title: Optional[str] = None,
    notes: str = "",
    theme: str = "nau_an",
    genre: Optional[str] = None,
    target_skill: Optional[str] = None,
    tiktok_full_duration: int = 0
) -> Dict[str, Any]:
    """Tạo một kịch bản thô (chờ AI hoàn thiện, tự động gán thể loại & Skill)"""
    detected_genre, detected_skill = detect_story_genre_and_skill(raw_content)
    final_genre = genre or detected_genre
    final_skill = target_skill or detected_skill

    first_line = raw_content.strip().split("\n")[0][:40] if raw_content.strip() else "Kịch bản thô"
    auto_title = title or f"[{final_genre.upper()}] {first_line}..."
    return create_project(
        title=auto_title,
        content="",
        raw_content=raw_content,
        status="0_ban_tho",
        notes=notes or f"Kịch bản thô ({final_genre} | {final_skill})",
        theme=theme,
        genre=final_genre,
        target_skill=final_skill,
        tiktok_full_duration=tiktok_full_duration
    )

def batch_create_raw_projects(raw_list: List[str], theme: str = "nau_an") -> List[Dict[str, Any]]:
    """Tạo hàng loạt kịch bản thô cùng lúc"""
    results = []
    for raw in raw_list:
        clean = raw.strip()
        if clean:
            p = create_raw_project(clean, theme=theme)
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

def toggle_tiktok_posted(project_id: str) -> Optional[Dict[str, Any]]:
    """Đảo trạng thái đã đăng TikTok (1: đã đăng, 0: đang chờ up)"""
    p = get_project(project_id)
    if not p:
        return None
    curr_val = p.get("tiktok_posted", 0)
    if curr_val:
        return update_project(project_id, tiktok_posted=0)
    else:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ep = p.get("ytb_episode")
        is_even = (int(ep) % 2 == 0) if (ep is not None) else False
        account = "kenh_chan" if is_even else "kenh_le"
        return update_project(project_id, tiktok_posted=1, tiktok_posted_at=now_str, tiktok_account=account)

import shutil
import glob

CAPCUT_DRAFT_ROOT = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")

def clean_project_files(project_id: str):
    """
    Xóa sạch toàn bộ dữ liệu của kịch bản:
    - Thư mục YouTube outputs/youtube/KBxxx/
    - Video & file text TikTok trong outputs/tiktok_ready/
    - Thư mục lưu trữ outputs/archives/KBxxx/
    - Thư mục legacy outputs/KBxxx/ nếu còn
    - Draft dự án trong CapCut PC
    """
    if not project_id:
        return
    
    for folder in [
        os.path.join(YOUTUBE_DIR, project_id),
        os.path.join(ARCHIVES_DIR, project_id),
        os.path.join(OUTPUTS_DIR, project_id)
    ]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception as e:
                print(f"[Delete] Lỗi xóa thư mục {folder}: {e}")

    # Xóa file video & txt trong tiktok_ready
    if os.path.exists(TIKTOK_READY_DIR):
        for f in os.listdir(TIKTOK_READY_DIR):
            if f.startswith(project_id):
                fp = os.path.join(TIKTOK_READY_DIR, f)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass

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
    Đồng bộ chính xác trạng thái file thực tế trong:
    - outputs/youtube/KBxxx (Video YouTube & Thumbnail)
    - outputs/tiktok_ready (Video TikTok & Text file số tập)
    - outputs/archives/KBxxx (Voice Audio & Script)
    """
    p = get_project(pid)
    if not p:
        return None
    
    yt_dir = os.path.join(YOUTUBE_DIR, pid)
    arch_dir = os.path.join(ARCHIVES_DIR, pid)
    legacy_dir = os.path.join(OUTPUTS_DIR, pid)
    
    found_audio = None
    found_tt = None
    found_yt = None
    found_th = None
    
    # 1. Quét YouTube folder
    if os.path.exists(yt_dir):
        for f in os.listdir(yt_dir):
            fl = f.lower()
            fp = os.path.join(yt_dir, f)
            if os.path.isdir(fp):
                continue
            if fl.endswith((".png", ".jpg", ".jpeg", ".webp")) and not found_th:
                found_th = fp
            elif fl.endswith((".mp4", ".mov", ".mkv")) and not found_yt:
                found_yt = fp
                
    # 2. Quét TikTok video trong tiktok_ready
    if os.path.exists(TIKTOK_READY_DIR):
        for f in os.listdir(TIKTOK_READY_DIR):
            fl = f.lower()
            if fl.startswith(pid.lower()) and fl.endswith((".mp4", ".mov", ".mkv")):
                found_tt = os.path.join(TIKTOK_READY_DIR, f)
                break
                
    # 3. Quét Audio trong archives
    if os.path.exists(arch_dir):
        for f in os.listdir(arch_dir):
            fl = f.lower()
            fp = os.path.join(arch_dir, f)
            if fl.endswith((".wav", ".mp3", ".m4a")) and not found_audio:
                found_audio = fp
                
    # Fallback legacy folder nếu chưa migrate
    if os.path.exists(legacy_dir) and os.path.isdir(legacy_dir):
        for f in os.listdir(legacy_dir):
            fl = f.lower()
            fp = os.path.join(legacy_dir, f)
            if os.path.isdir(fp):
                continue
            if fl.endswith((".wav", ".mp3", ".m4a")) and not found_audio:
                found_audio = fp
            elif fl.endswith((".mp4", ".mov", ".mkv")):
                if ("tiktok" in fl or "doc" in fl) and not found_tt:
                    found_tt = fp
                elif not found_yt:
                    found_yt = fp
            elif fl.endswith((".png", ".jpg", ".jpeg", ".webp")) and not found_th:
                found_th = fp

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

    updates["package_dir"] = yt_dir

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

    # Tự động đồng bộ số tập vào file text TikTok nếu có video TikTok và có số tập
    ep = p.get("ytb_episode")
    if found_tt and ep is not None:
        sync_tiktok_episode_file(pid, ep)

    if updates:
        return update_project(pid, **updates)
    return p

def sync_all_projects() -> List[Dict[str, Any]]:
    """Đồng bộ thực tế tất cả các kịch bản với thư mục outputs/"""
    projects = get_all_projects()
    for p in projects:
        sync_project_files(p["id"])
    return get_all_projects()


def toggle_tiktok_full_duration(project_id: str) -> Optional[Dict[str, Any]]:
    """Bật / tắt chế độ lấy Full độ dài video cho TikTok (15p vs Full)"""
    p = get_project(project_id)
    if not p:
        return None
    curr = p.get("tiktok_full_duration", 0)
    new_val = 0 if curr else 1
    return update_project(project_id, tiktok_full_duration=new_val)
