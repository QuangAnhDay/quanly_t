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
    trim_trailing_silence(output_path)
    return output_path

def trim_trailing_silence(audio_path: str, max_silence_sec: float = 0.3) -> str:
    """
    Tự động quét biên độ âm thanh cuối file audio và cắt tỉa khoảng im lặng thừa (> max_silence_sec).
    """
    if not os.path.exists(audio_path):
        return audio_path

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd_detect = [
            ffmpeg_exe, "-y",
            "-i", audio_path,
            "-af", "silencedetect=noise=-40dB:d=0.3",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd_detect, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
        
        starts = re.findall(r"silence_start:\s*(\d+\.\d+|\d+)", res.stderr)
        if not starts:
            return audio_path

        m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if not m_dur:
            return audio_path

        dur = int(m_dur.group(1))*3600 + int(m_dur.group(2))*60 + float(m_dur.group(3))
        last_silence_start = float(starts[-1])

        if dur - last_silence_start > max_silence_sec and last_silence_start > 0.5:
            target_dur = last_silence_start + max_silence_sec
            tmp_trimmed = audio_path + ".tmp_trimmed.mp3"
            cmd_trim = [
                ffmpeg_exe, "-y",
                "-i", audio_path,
                "-t", str(target_dur),
                "-c", "copy",
                tmp_trimmed
            ]
            subprocess.run(cmd_trim, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(tmp_trimmed) and os.path.getsize(tmp_trimmed) > 1000:
                os.replace(tmp_trimmed, audio_path)
    except Exception as e:
        print(f"Warning: Silence trimming failed: {e}")
    return audio_path


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
