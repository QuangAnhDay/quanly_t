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
    output_path: Optional[str] = None,
    on_progress = None
) -> str:
    """
    Tạo file giọng đọc tiếng Việt bằng edge-tts hoặc VoiceStudio (giọng clone).
    """
    if not output_path:
        if not (output_filename.endswith(".mp3") or output_filename.endswith(".wav")):
            output_filename += ".mp3"
        output_path = os.path.join(AUDIO_DIR, output_filename)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Kiểm tra xem voice có thuộc VoiceStudio (tiền tố 'voicestudio:' hoặc ID clone)
    is_vs_voice = False
    clean_voice_id = voice
    
    if voice and voice.startswith("voicestudio:"):
        is_vs_voice = True
        clean_voice_id = voice.replace("voicestudio:", "")
    else:
        # Nếu không có tiền tố, thử đối chiếu danh sách voice clone từ VoiceStudio
        try:
            import voicestudio_service
            if voicestudio_service.is_voicestudio_available():
                vs_voices = voicestudio_service.get_voicestudio_voices()
                for v in vs_voices:
                    vid = v.get("voice_id") or v.get("id")
                    if vid and vid == voice:
                        is_vs_voice = True
                        clean_voice_id = vid
                        break
        except Exception:
            pass

    if is_vs_voice:
        import voicestudio_service
        voicestudio_service.ensure_voicestudio_running()
        return await voicestudio_service.generate_voicestudio_file_async(
            text=text,
            output_path=output_path,
            voice=clean_voice_id,
            on_progress=on_progress
        )

    # 2. Tạo bằng Edge-TTS nếu không phải giọng clone VoiceStudio
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice or DEFAULT_VOICE,
        rate=rate or "+0%",
        pitch=pitch or "+0Hz"
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
