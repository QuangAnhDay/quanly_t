import os
import sys
import time
import requests
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import database
import audio_engine
import video_engine

print("=== BẮT ĐẦU KIỂM THỬ HỆ THỐNG TRUYỆN ===")

# 1. Kiểm tra Database
print("\n[1/4] Kiểm tra Database...")
test_p = database.create_project(
    title="Truyện cổ tích Cây Tre Trăm Đốt",
    content="Ngày xửa ngày xưa, ở một ngôi làng nọ, có một anh nông dân nghèo nhưng vô cùng hiền lành và chịu khó làm lụng.",
    status="1_cho_duyet"
)
print(f"-> Tạo thành công: ID={test_p['id']}, Title={test_p['title']}")

# 2. Kiểm tra Audio Engine (Edge-TTS)
print("\n[2/4] Kiểm tra Audio Engine (Edge-TTS)...")
audio_file = audio_engine.generate_speech_sync(
    text=test_p['content'],
    output_filename=f"{test_p['id']}.mp3",
    voice="vi-VN-HoaiMyNeural"
)
print(f"-> File âm thanh đã tạo: {audio_file}")
assert os.path.exists(audio_file), "File audio không tồn tại!"
database.update_project(test_p['id'], audio_path=audio_file, status="3_da_co_audio")

# 3. Kiểm tra Video Engine (FFmpeg)
print("\n[3/4] Kiểm tra Video Engine (FFmpeg)...")
video_file = video_engine.render_video(
    audio_path=audio_file,
    output_filename=f"{test_p['id']}.mp4",
    title=test_p['title']
)
print(f"-> Video thành phẩm đã render: {video_file}")
assert os.path.exists(video_file), "File video không tồn tại!"
database.update_project(test_p['id'], video_path=video_file, status="4_da_render_video")

# 4. Kiểm tra cập nhật trạng thái trong Database
print("\n[4/4] Kiểm tra trạng thái cuối cùng...")
final_p = database.get_project(test_p['id'])
print(f"-> Kịch bản {final_p['id']} hiện có trạng thái: {final_p['status']}")
print(f"-> Audio: {final_p['audio_path']}")
print(f"-> Video: {final_p['video_path']}")

print("\n=== TẤT CẢ CÁC BƯỚC KIỂM THỬ ĐÃ HOÀN TẤT THÀNH CÔNG 100%! ===")
