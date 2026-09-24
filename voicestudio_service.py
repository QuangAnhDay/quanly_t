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

def textToSpeech(text: str, options: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Hàm chuyển đổi Văn bản -> Âm thanh (Text-To-Speech) đồng bộ tương thích OpenAI Audio API.
    
    :param text: Đoạn văn bản cần chuyển thành giọng nói (bắt buộc).
    :param options: Dictionary tùy chọn:
           - voice: Tên cấu hình giọng nói (mặc định: "default")
           - outputFormat: Định dạng file xuất ra ("mp3" hoặc "wav", mặc định "mp3")
           - timeout: Thời gian tối đa đợi response (giây, mặc định 120)
    :return: Dữ liệu âm thanh dạng bytes
    """
    if not text or not text.strip():
        raise ValueError("Nội dung văn bản (text) không được để trống!")
        
    options = options or {}
    voice = options.get("voice", "default")
    output_format = options.get("outputFormat") or options.get("output_format", "mp3")
    timeout = options.get("timeout", 120)
    
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
    
    try:
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Lỗi khi kết nối VoiceStudio API tại {endpoint_url}: {e}")

async def textToSpeechAsync(text: str, options: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Hàm chuyển đổi Văn bản -> Âm thanh (Text-To-Speech) bất đồng bộ (Async) cho FastAPI / asyncio.
    """
    if not text or not text.strip():
        raise ValueError("Nội dung văn bản (text) không được để trống!")
        
    options = options or {}
    voice = options.get("voice", "default")
    output_format = options.get("outputFormat") or options.get("output_format", "mp3")
    timeout = options.get("timeout", 120)
    
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
    
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        try:
            async with session.post(endpoint_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    raise RuntimeError(f"VoiceStudio API trả về mã lỗi {resp.status}: {err_text}")
                return await resp.read()
        except Exception as e:
            raise RuntimeError(f"Lỗi khi kết nối VoiceStudio API bất đồng bộ tại {endpoint_url}: {e}")

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
