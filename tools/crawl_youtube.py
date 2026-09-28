import os
import re
import sys
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "competitor_scripts")

def clean_text(text: str) -> str:
    """Làm sạch văn bản phụ đề"""
    text = re.sub(r"\[.*?\]", "", text) # Bỏ các thẻ [Âm nhạc], [Tiếng cười]...
    text = re.sub(r"\s+", " ", text)    # Xóa khoảng trắng thừa
    return text.strip()

def get_video_id(url: str) -> str:
    """Trích xuất Video ID từ URL YouTube"""
    match = re.search(r"(?:v=|\/shorts\/|\/embed\/|\/v\/|youtu\.be\/|\/watch\?v=)([^#&?]{11})", url)
    return match.group(1) if match else url

def fetch_transcript_single(url_or_id: str, lang: str = "vi") -> str:
    """Cào kịch bản của 1 video đơn lẻ"""
    vid = get_video_id(url_or_id)
    try:
        # Thử lấy phụ đề tiếng Việt
        transcript_list = YouTubeTranscriptApi.get_transcript(vid, languages=[lang, 'vi', 'en'])
        full_text = " ".join([clean_text(item['text']) for item in transcript_list if item['text']])
        return full_text
    except Exception as e:
        print(f"⚠️ Không thể cào phụ đề video [{vid}]: {e}")
        return ""

def fetch_channel_videos(channel_url: str, max_results: int = 15) -> list:
    """Lấy danh sách ID video từ kênh YouTube"""
    ydl_opts = {
        'extract_flat': True,
        'playlistend': max_results,
        'quiet': True
    }
    video_ids = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    if entry and 'id' in entry:
                        video_ids.append((entry['id'], entry.get('title', entry['id'])))
        except Exception as e:
            print(f"❌ Lỗi khi quét kênh {channel_url}: {e}")
    return video_ids

def crawl_batch_urls(urls: list, output_folder: str = OUTPUT_DIR):
    """Cào kịch bản từ danh sách các URL video"""
    os.makedirs(output_folder, exist_ok=True)
    success_count = 0
    
    print(f"🚀 Bắt đầu cào {len(urls)} kịch bản YouTube...")
    for idx, url in enumerate(urls, 1):
        vid = get_video_id(url)
        print(f"[{idx}/{len(urls)}] Đang cào [{vid}]...")
        text = fetch_transcript_single(vid)
        
        if text and len(text) > 50:
            filename = f"script_{vid}.txt"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"   ✅ Đã lưu vào {filepath} ({len(text)} ký tự)")
            success_count += 1
        else:
            print(f"   ❌ Không có phụ đề khả dụng cho {vid}")
            
    print(f"\n🎉 HOÀN THÀNH! Đã lưu thành công {success_count}/{len(urls)} kịch bản vào '{output_folder}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if "channel" in target or "@" in target or "playlist" in target:
            print(f"🔍 Quét kênh YouTube: {target}")
            videos = fetch_channel_videos(target, max_results=15)
            urls = [f"https://www.youtube.com/watch?v={v[0]}" for v in videos]
            crawl_batch_urls(urls)
        else:
            crawl_batch_urls([target])
    else:
        print("Cách dùng:")
        print("  .venv\\Scripts\\python.exe tools\\crawl_youtube.py <URL_VIDEO_HOAC_KENH>")
