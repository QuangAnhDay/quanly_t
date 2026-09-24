import os
import sys
import time
import subprocess
import sqlite3
import requests
import aiohttp
import asyncio
from typing import Optional, Dict, Any, Union, List

# 1. Cấu hình Base URL qua biến môi trường (mặc định http://127.0.0.1:3900/v1)
DEFAULT_BASE_URL = "http://127.0.0.1:3900/v1"

def get_base_url() -> str:
    """Lấy Base URL của VoiceStudio API từ biến môi trường hoặc mặc định"""
    url = os.environ.get("VOICESTUDIO_API_URL", DEFAULT_BASE_URL).rstrip("/")
    return url

import re

MAX_CHUNK_CHARS = 2500

def split_text_into_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """
    Chia văn bản dài thành các đoạn nhỏ dưới max_chars (mặc định 2500 ký tự) ngắt theo dòng và câu.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n")
    current_chunk = ""

    for para in paragraphs:
        para_str = para.strip()
        if not para_str:
            continue
            
        if len(para_str) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            sentences = re.split(r'(?<=[.!?;\n])\s+', para_str)
            sub_chunk = ""
            for sentence in sentences:
                sentence_str = sentence.strip()
                if not sentence_str:
                    continue
                if len(sub_chunk) + len(sentence_str) + 1 <= max_chars:
                    sub_chunk = f"{sub_chunk} {sentence_str}".strip()
                else:
                    if sub_chunk:
                        chunks.append(sub_chunk)
                    while len(sentence_str) > max_chars:
                        space_idx = sentence_str.rfind(' ', 0, max_chars)
                        if space_idx > 0:
                            chunks.append(sentence_str[:space_idx].strip())
                            sentence_str = sentence_str[space_idx:].strip()
                        else:
                            chunks.append(sentence_str[:max_chars].strip())
                            sentence_str = sentence_str[max_chars:].strip()
                    sub_chunk = sentence_str
            if sub_chunk:
                chunks.append(sub_chunk)
        else:
            if len(current_chunk) + len(para_str) + 1 <= max_chars:
                current_chunk = f"{current_chunk}\n{para_str}".strip() if current_chunk else para_str
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para_str

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if c.strip()]


def textToSpeech(text: str, options: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Hàm chuyển đổi Văn bản -> Âm thanh (Text-To-Speech) đồng bộ tương thích OpenAI Audio API.
    """
    return asyncio.run(textToSpeechAsync(text, options))

async def _raw_single_speech_async(text: str, voice: str, output_format: str, timeout: int, session: aiohttp.ClientSession) -> bytes:
    base_url = get_base_url()
    endpoint_url = f"{base_url}/audio/speech"
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": output_format
    }
    headers = {
        "Content-Type": "application/json"
    }
    async with session.post(endpoint_url, json=payload, headers=headers) as resp:
        if resp.status != 200:
            err_text = await resp.text()
            raise RuntimeError(f"VoiceStudio API trả về mã lỗi {resp.status}: {err_text}")
        return await resp.read()

async def textToSpeechAsync(text: str, options: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Hàm chuyển đổi Văn bản -> Âm thanh (Text-To-Speech) bất đồng bộ với tự động chia nhỏ văn bản dài.
    """
    if not text or not text.strip():
        raise ValueError("Nội dung văn bản (text) không được để trống!")
        
    options = options or {}
    voice = options.get("voice", "default")
    output_format = options.get("outputFormat") or options.get("output_format", "mp3")
    timeout = options.get("timeout", 180)
    
    chunks = split_text_into_chunks(text, max_chars=MAX_CHUNK_CHARS)
    if not chunks:
        raise ValueError("Nội dung kịch bản rỗng!")
        
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        audio_parts = []
        for i, chunk in enumerate(chunks):
            try:
                data = await _raw_single_speech_async(chunk, voice, output_format, timeout, session)
                audio_parts.append(data)
            except Exception as e:
                raise RuntimeError(f"Lỗi khi kết nối VoiceStudio API tại đoạn {i+1}/{len(chunks)}: {e}")
        return b"".join(audio_parts)

def generate_voicestudio_file(text: str, output_path: str, voice: str = "default", output_format: str = "mp3") -> str:
    """
    Tạo giọng đọc từ VoiceStudio và ghi thẳng ra file đĩa.
    """
    audio_bytes = textToSpeech(text, {"voice": voice, "outputFormat": output_format})
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    return output_path

async def generate_voicestudio_file_async(text: str, output_path: str, voice: str = "default", output_format: str = "mp3") -> str:
    """
    Tạo giọng đọc từ VoiceStudio bất đồng bộ và ghi thẳng ra file đĩa.
    """
    audio_bytes = await textToSpeechAsync(text, {"voice": voice, "outputFormat": output_format})
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    return output_path

def get_voicestudio_voices() -> List[Dict[str, Any]]:
    """
    Lấy danh sách các giọng đọc đã clone từ VoiceStudio.
    1. Gọi HTTP API GET /v1/audio/voices nếu VoiceStudio đang chạy.
    2. Nếu rỗng/lỗi, đọc trực tiếp từ SQLite database omnivoice.db trong APPDATA.
    """
    base_url = get_base_url()
    try:
        resp = requests.get(f"{base_url}/audio/voices", timeout=2)
        if resp.status_code == 200:
            raw_voices = resp.json().get("voices", [])
            profiles = [v for v in raw_voices if v.get("type") == "profile"]
            if profiles:
                return profiles
    except Exception:
        pass

    # Fallback: Đọc từ sqlite3 DB của VoiceStudio
    appdata = os.environ.get("APPDATA", "")
    db_path = os.path.join(appdata, "OmniVoice", "omnivoice.db")
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, name, language FROM voice_profiles ORDER BY name").fetchall()
        profiles = []
        for r in rows:
            profiles.append({
                "voice_id": r["id"],
                "name": r["name"],
                "language": r["language"] or "Vietnamese",
                "type": "profile"
            })
        conn.close()
        return profiles
    except Exception as e:
        print(f"[VoiceStudio] Lỗi đọc DB local ({db_path}): {e}")
        return []

def is_voicestudio_available() -> bool:
    """Kiểm tra xem VoiceStudio API Server có đang hoạt động hay không"""
    try:
        base_url = get_base_url()
        resp = requests.get(base_url, timeout=2)
        return resp.status_code in [200, 404]
    except Exception:
        return False

VOICESTUDIO_DIR = r"D:\myProject\voice"
VOICESTUDIO_PYTHON = os.path.join(VOICESTUDIO_DIR, ".venv", "Scripts", "python.exe")

def ensure_voicestudio_running() -> bool:
    """Kiểm tra và tự động bật VoiceStudio API Server (Port 3900) ngầm nếu chưa chạy"""
    if is_voicestudio_available():
        return True

    if not os.path.exists(VOICESTUDIO_DIR):
        return False

    py_exe = VOICESTUDIO_PYTHON if os.path.exists(VOICESTUDIO_PYTHON) else sys.executable

    try:
        subprocess.Popen(
            [py_exe, "backend/main.py"],
            cwd=VOICESTUDIO_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        for _ in range(6):
            time.sleep(0.5)
            if is_voicestudio_available():
                return True
        return True
    except Exception as e:
        print(f"[VoiceStudio] Lỗi khi tự động mở VoiceStudio Backend: {e}")
        return False

if __name__ == "__main__":
    print(f"VoiceStudio API Base URL: {get_base_url()}")
    print(f"Trạng thái kết nối Server: {'Khả dụng' if is_voicestudio_available() else 'Chưa bật Server tại port 3900'}")
