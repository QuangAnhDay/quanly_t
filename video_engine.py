import os
import subprocess
import glob
import random
import imageio_ffmpeg

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
PROJECT_DIR = os.path.dirname(__file__)
BG_DIR = os.path.join(PROJECT_DIR, "backgrounds")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "3_video_output")

def get_audio_duration(audio_path: str) -> float:
    """Lấy thời lượng file audio bằng ffmpeg/ffprobe"""
    cmd = [
        FFMPEG_PATH,
        "-i", audio_path,
        "-f", "null",
        "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    # Tìm dòng Duration: 00:00:05.12
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 10.0 # fallback

def render_video(
    audio_path: str,
    output_filename: str,
    title: str = "",
    aspect_ratio: str = "9:16" # "9:16" (TikTok/Shorts) hoặc "16:9" (YouTube dài)
) -> str:
    """
    Render video thành phẩm bằng FFmpeg.
    Tự động ghép background video từ backgrounds/ (nếu có) hoặc tạo nền thẩm mỹ tự động.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(BG_DIR, exist_ok=True)

    if not output_filename.endswith(".mp4"):
        output_filename += ".mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    duration = get_audio_duration(audio_path)
    
    # Tìm video nền trong thư mục backgrounds/
    bg_candidates = glob.glob(os.path.join(BG_DIR, "*.mp4"))
    
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

    if bg_candidates:
        bg_file = random.choice(bg_candidates)
        # Ghép video nền lặp lại + audio
        cmd = [
            FFMPEG_PATH, "-y",
            "-stream_loop", "-1",
            "-i", bg_file,
            "-i", audio_path,
            "-t", str(duration),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
    else:
        # Tự động tạo video nền chuyển màu sóng âm thẩm mỹ (Audiogram)
        # Nền gradient sẫm màu + sóng âm thanh
        filter_complex = (
            f"[1:a]showwaves=s={width}x300:mode=p2p:colors=#38bdf8:scale=sqrt[wave]; "
            f"color=c=#0f172a:s={width}x{height}:d={duration}[bg]; "
            f"[bg][wave]overlay=(W-w)/2:(H-h)/2[v]"
        )
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "lavfi", "-i", f"color=c=#0f172a:s={width}x{height}:d={duration}",
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "1:a",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

if __name__ == "__main__":
    audio_test = os.path.join(PROJECT_DIR, "2_audio_input", "test_audio.mp3")
    if os.path.exists(audio_test):
        print("Đang render thử nghiệm video...")
        v_out = render_video(audio_test, "test_render.mp4", title="Kiểm tra hệ thống")
        print(f"Render video thành công tại: {v_out}")
