import os
import sys
import re
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Any

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import task_logger

COMPETITOR_CHANNELS = [
    {
        "name": "Điểm Điểm Audio",
        "url": "https://www.youtube.com/@Diemdiemaudione",
        "channel_id": "UCMwRmqJoW4TVcCgG3GskOzw",
        "default_genre": "hohang",
        "default_skill": "/kichban-audio-hohang"
    },
    {
        "name": "Kho Báu Trọng Sinh",
        "url": "https://www.youtube.com/@KhoB%C3%A1uTr%E1%BB%8DngSinh",
        "channel_id": "UC6C1N3cEp9y0fbJ4XlxRyUQ",
        "default_genre": "giadinh_vochong",
        "default_skill": "/kichban-audio-giadinh-vochong"
    },
    {
        "name": "Dứa Audio",
        "url": "https://www.youtube.com/@DuaAudio-n8u",
        "channel_id": "UC11nn9xseTJhOkfvLhvqhZw",
        "default_genre": "nu_chinh",
        "default_skill": "/kichban-nu-chinh"
    }
]

def fetch_channel_latest_videos(channel_id: str, limit: int = 2) -> List[Dict[str, str]]:
    """Lấy danh sách video mới nhất từ RSS Feed chính thức của kênh YouTube"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    videos = []
    try:
        r = requests.get(rss_url, timeout=12)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
            entries = root.findall('atom:entry', ns)
            for e in entries[:limit]:
                title = e.find('atom:title', ns).text
                vid_id = e.find('yt:videoId', ns).text
                published = e.find('atom:published', ns).text
                videos.append({
                    "id": vid_id,
                    "title": title,
                    "published": published,
                    "url": f"https://www.youtube.com/watch?v={vid_id}"
                })
    except Exception as e:
        print(f"[CompetitorSpy] Lỗi tải RSS {channel_id}: {e}")
    return videos

def fetch_video_transcript(video_id: str) -> str:
    """Bóc tách phụ đề / lời thoại video YouTube trong 2 giây"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t = YouTubeTranscriptApi().fetch(video_id, languages=['vi', 'vi-VN', 'en'])
        return " ".join([x.text for x in t])
    except Exception as e:
        print(f"[CompetitorSpy] Không lấy được transcript {video_id}: {e}")
        return ""

def scan_all_competitors(limit_per_channel: int = 1) -> List[Dict[str, Any]]:
    """Do thám toàn bộ các kênh đối thủ và thu thập kịch bản gốc"""
    results = []
    for ch in COMPETITOR_CHANNELS:
        print(f"📡 Đang do thám kênh: {ch['name']}...")
        vids = fetch_channel_latest_videos(ch["channel_id"], limit=limit_per_channel)
        for v in vids:
            print(f"   • Phát hiện video mới: {v['title']} ({v['id']})")
            transcript = fetch_video_transcript(v["id"])
            item = {
                "channel": ch["name"],
                "video_id": v["id"],
                "title": v["title"],
                "published": v["published"],
                "url": v["url"],
                "transcript": transcript,
                "default_genre": ch["default_genre"],
                "default_skill": ch["default_skill"]
            }
            results.append(item)
    return results

def inject_raw_script(
    raw_content: str,
    title: Optional[str] = None,
    genre: Optional[str] = None,
    target_skill: Optional[str] = None,
    tiktok_full_duration: int = 0,
    theme: str = "nau_an"
) -> Dict[str, Any]:
    """Bắn kịch bản thô vào Database truyen.db, tự động gán thể loại & Skill"""
    database.init_db()
    proj = database.create_raw_project(
        raw_content=raw_content,
        title=title,
        genre=genre,
        target_skill=target_skill,
        tiktok_full_duration=tiktok_full_duration,
        theme=theme
    )
    print(f"✅ Đã tạo kịch bản [{proj['id']}]: {proj['title']} (Skill: {proj.get('target_skill')})")
    task_logger.add_log("pipeline", f"📝 [Tự Động Hóa] Đã nạp kịch bản [{proj['id']}] ({proj.get('genre')}) vào kho chờ Claude!", "success", proj['id'])
    return proj

def dispatch_pending_claude(profile_count: int = 5):
    """Mở đồng loạt các Profile Chrome để Claude hoàn thiện các kịch bản thô đang chờ"""
    database.init_db()
    pending = database.get_pending_raw_projects()
    if not pending:
        print("ℹ️ Không có kịch bản thô nào đang chờ xử lý.")
        return []

    # Đọc config để lấy danh sách profile
    cfg_path = os.path.join(BASE_DIR, "config.json")
    chrome_profiles = ["Profile 7", "Profile 2", "Profile 4", "Profile 5", "Profile 1"]
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                chrome_profiles = cfg.get("chrome_profiles", chrome_profiles)
        except Exception:
            pass

    selected_profiles = chrome_profiles[:min(len(pending), len(chrome_profiles), profile_count)]
    import subprocess
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")

    launched = []
    for idx, pid in enumerate(selected_profiles):
        target_kb = pending[idx]["id"]
        target_url = f"https://claude.ai/new?auto_kb={target_kb}&profile_id={pid}"
        cmd = f'"{chrome_path}" --profile-directory="{pid}" "{target_url}"'
        subprocess.Popen(cmd, shell=True)
        launched.append({"profile": pid, "kb": target_kb})
        print(f"🚀 Đã mở Chrome [{pid}] gán kịch bản [{target_kb}]")

    return launched

if __name__ == "__main__":
    if "--scan" in sys.argv:
        vids = scan_all_competitors(limit_per_channel=1)
        print(f"\nĐã quét xong {len(vids)} video từ đối thủ.")
    elif "--dispatch" in sys.argv:
        dispatch_pending_claude()
    else:
        print("Competitor Spy & Auto Pipeline Module Ready.")
