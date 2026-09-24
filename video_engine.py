import os
import subprocess
import glob
import random
import re
import math
import imageio_ffmpeg

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
PROJECT_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")
BG_DIR = os.path.join(PROJECT_DIR, "backgrounds")



def get_audio_duration(file_path: str) -> float:
    """Lấy thời lượng file audio/video bằng ffmpeg"""
    cmd = [
        FFMPEG_PATH,
        "-i", file_path,
        "-f", "null",
        "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 10.0

def convert_16x9_to_9x16(
    input_video_path: str,
    output_video_path: str,
    style: str = "blur" # "blur" (nền mờ cinematic) hoặc "crop" (phóng to full)
) -> str:
    """
    Tự động chuyển đổi video ngang 16:9 (YouTube) sang dọc 9:16 (TikTok) siêu tốc.
    - Giữ nguyên 100% âm thanh & phụ đề đã có từ CapCut.
    - Chạy cực nhanh bằng GPU / Fast Encoder (chỉ 10-15s cho video ngắn, vài phút cho video 50p).
    """
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Không tìm thấy file video nguồn: {input_video_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    if style == "blur":
        # Filter: Lớp nền phóng to + làm mờ (boxblur), lớp trước giữ nguyên tỷ lệ sắc nét ở giữa
        filter_complex = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            "[0:v]scale=1080:-2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
    else:
        # Crop giữa
        filter_complex = "[0:v]scale=-2:1920,crop=1080:1920[v]"

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", input_video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "copy", # Copy thẳng audio không cần encode lại
        output_video_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        # Nếu copy audio lỗi (ví dụ không tương thích container), encode aac
        cmd[-3] = "aac"
        cmd.insert(-2, "-b:a")
        cmd.insert(-2, "192k")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return output_video_path

def split_video_into_parts(
    input_video_path: str,
    output_dir: str,
    part_prefix: str = "Part",
    part_duration_sec: int = 180 # 3 phút mỗi tập
) -> list:
    """
    Cắt video dài (ví dụ 50 phút) thành chuỗi các tập ngắn (Part 1, Part 2...) cho TikTok.
    Sử dụng chế độ Stream Copy siêu tốc (cắt video 50p chỉ mất ~5 giây).
    """
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Không tìm thấy video: {input_video_path}")

    os.makedirs(output_dir, exist_ok=True)
    total_duration = get_audio_duration(input_video_path)
    total_parts = math.ceil(total_duration / part_duration_sec)

    created_parts = []
    for i in range(total_parts):
        start_sec = i * part_duration_sec
        part_num = i + 1
        out_filename = f"{part_prefix}_tap_{part_num:02d}.mp4"
        out_path = os.path.join(output_dir, out_filename)

        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(start_sec),
            "-i", input_video_path,
            "-t", str(part_duration_sec),
            "-c", "copy",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(out_path):
            created_parts.append(out_path)

    return created_parts

def render_video(
    audio_path: str,
    output_filename: str,
    title: str = "",
    aspect_ratio: str = "9:16"
) -> str:
    """Render video dự phòng bằng FFmpeg"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(BG_DIR, exist_ok=True)

    if not output_filename.endswith(".mp4"):
        output_filename += ".mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    duration = get_audio_duration(audio_path)
    
    bg_candidates = glob.glob(os.path.join(BG_DIR, "*.mp4"))
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

    if bg_candidates:
        bg_file = random.choice(bg_candidates)
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
        filter_complex = (
            f"[1:a]showwaves=s={width}x300:mode=p2p:colors=#8b5cf6:scale=sqrt[wave]; "
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
