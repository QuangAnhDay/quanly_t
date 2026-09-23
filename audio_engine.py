import os
import asyncio
import edge_tts
from typing import Optional

DEFAULT_VOICE = "vi-VN-HoaiMyNeural"
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "2_audio_input")

async def generate_speech(
    text: str,
    output_filename: str = "voice.mp3",
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    output_path: Optional[str] = None
) -> str:
    """
    Tạo file giọng đọc tiếng Việt bằng edge-tts chất lượng cao.
    """
    if not output_path:
        if not (output_filename.endswith(".mp3") or output_filename.endswith(".wav")):
            output_filename += ".mp3"
        output_path = os.path.join(AUDIO_DIR, output_filename)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Cấu hình communicate
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )
    
    await communicate.save(output_path)
    return output_path


def generate_speech_sync(
    text: str,
    output_filename: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> str:
    """Hàm bọc đồng bộ cho các ngữ cảnh gọi không async."""
    return asyncio.run(generate_speech(text, output_filename, voice, rate, pitch))

if __name__ == "__main__":
    test_text = "Xin chào các bạn. Đây là bài kiểm tra giọng đọc tiếng Việt tự động cho kịch bản video của bạn."
    res = generate_speech_sync(test_text, "test_audio.mp3")
    print(f"Đã tạo file kiểm tra thành công tại: {res}")
