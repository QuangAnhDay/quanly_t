import os
import sys
import json
import uuid
import time
import glob
import random
import re
import subprocess
import unicodedata
import imageio_ffmpeg

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CAPCUT_DRAFT_ROOT = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")

# Thư mục chứa video nền theo chủ đề
BG_BASE_DIR = os.path.join(PROJECT_DIR, "backgrounds")
THEMES = ["nau_an", "handmade"]

def remove_accents(text: str) -> str:
    """Xóa dấu tiếng Việt để tạo tên thư mục chuẩn ASCII an toàn tuyệt đối trên Windows"""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return text

def init_theme_folders():
    """Tạo sẵn các thư mục chủ đề trong backgrounds/"""
    for t in THEMES:
        os.makedirs(os.path.join(BG_BASE_DIR, t), exist_ok=True)
        gk = os.path.join(BG_BASE_DIR, t, ".gitkeep")
        if not os.path.exists(gk):
            open(gk, "w").close()

init_theme_folders()

def get_media_duration_and_size(file_path: str):
    """Lấy thời lượng (giây), chiều rộng và chiều cao của file video/audio"""
    cmd = [FFMPEG_PATH, "-i", file_path, "-f", "null", "-"]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    
    # Đo thời lượng
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    dur = (int(m_dur.group(1))*3600 + int(m_dur.group(2))*60 + float(m_dur.group(3))) if m_dur else 10.0
    
    # Đo kích thước video (nếu có)
    m_dim = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", res.stderr)
    w, h = (int(m_dim.group(1)), int(m_dim.group(2))) if m_dim else (1080, 1920)
    
    return dur, w, h

def get_theme_videos(theme: str = "nau_an"):
    """Lấy danh sách các file video thuộc chủ đề được chọn"""
    theme_dir = os.path.join(BG_BASE_DIR, theme)
    videos = []
    if os.path.exists(theme_dir):
        videos = glob.glob(os.path.join(theme_dir, "*.mp4")) + glob.glob(os.path.join(theme_dir, "*.mov"))
    
    # Fallback: nếu thư mục chủ đề trống, tìm trong thư mục backgrounds chung
    if not videos:
        videos = glob.glob(os.path.join(BG_BASE_DIR, "*.mp4")) + glob.glob(os.path.join(BG_BASE_DIR, "*.mov"))
        
    return [v.replace("\\", "/") for v in videos]

def get_theme_stats():
    """Trả về số lượng video trong từng chủ đề"""
    stats = {}
    for t in THEMES:
        v_list = get_theme_videos(t)
        stats[t] = len(v_list)
    return stats

def launch_capcut_app():
    """Khởi chạy ứng dụng CapCut PC"""
    capcut_exe = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe")
    if os.path.exists(capcut_exe):
        subprocess.Popen(f'"{capcut_exe}"', shell=True)
        return True
    return False

def create_capcut_draft(
    project_id: str,
    title: str,
    audio_path: str,
    theme: str = "nau_an"
) -> dict:
    """
    Tạo một Project CapCut hoàn chỉnh:
    1. Tự bốc ngẫu nhiên các video thuộc theme (nau_an hoặc handmade) sao cho đủ độ dài audio.
    2. Đặt các video lên Track Video (khớp khít, không thừa không thiếu).
    3. Đặt file audio lên Track Audio.
    4. Ghi thẳng vào thư mục Projects của CapCut PC và cập nhật root_meta_info.json.
    """
    if not os.path.exists(CAPCUT_DRAFT_ROOT):
        raise Exception(f"Không tìm thấy thư mục CapCut Drafts tại {CAPCUT_DRAFT_ROOT}")

    if not os.path.exists(audio_path):
        raise Exception(f"File audio không tồn tại tại {audio_path}")

    # Chuẩn hóa đường dẫn audio
    audio_path = os.path.abspath(audio_path).replace("\\", "/")
    audio_dur_sec, _, _ = get_media_duration_and_size(audio_path)
    total_duration_us = int(audio_dur_sec * 1_000_000)

    # Lấy kho video theo chủ đề
    video_files = get_theme_videos(theme)
    if not video_files:
        raise Exception(f"Kho video cho chủ đề '{theme}' đang trống! Vui lòng thêm video vào thư mục backgrounds/{theme}/")

    # Đo độ dài từng video
    video_info_list = []
    for vf in video_files:
        vdur, vw, vh = get_media_duration_and_size(vf)
        video_info_list.append({
            "path": vf,
            "duration_us": int(vdur * 1_000_000),
            "width": vw,
            "height": vh
        })

    # Bốc ngẫu nhiên các video nối tiếp nhau cho đủ độ dài audio
    random.shuffle(video_info_list)
    selected_clips = []
    current_acc_us = 0
    idx = 0

    while current_acc_us < total_duration_us:
        clip = video_info_list[idx % len(video_info_list)]
        clip_dur = clip["duration_us"]
        needed = total_duration_us - current_acc_us
        
        # Nếu clip dài hơn phần còn thiếu, cắt gọn đoạn cuối
        actual_dur = min(clip_dur, needed)
        selected_clips.append({
            "path": clip["path"],
            "width": clip["width"],
            "height": clip["height"],
            "source_start": 0,
            "duration": actual_dur,
            "timeline_start": current_acc_us
        })
        current_acc_us += actual_dur
        idx += 1

    # Tạo UUID và tên thư mục an toàn
    draft_id = str(uuid.uuid4()).upper()
    now_us = int(time.time() * 1_000_000)
    ascii_title = remove_accents(title)
    clean_title = re.sub(r'[^a-zA-Z0-9_ ]+', '', ascii_title).strip()
    safe_folder_name = f"{project_id}_{clean_title[:30]}".replace(" ", "_")
    draft_dir = os.path.join(CAPCUT_DRAFT_ROOT, safe_folder_name)
    os.makedirs(draft_dir, exist_ok=True)

    # Tên hiển thị trên màn hình CapCut
    display_name = f"{project_id} - {title[:35]}"

    # 1. Materials
    materials = {
        "videos": [],
        "audios": [],
        "speeds": [],
        "canvases": [],
        "transitions": [],
        "texts": [],
        "stickers": [],
        "effects": [],
        "images": []
    }

    speed_normal_id = str(uuid.uuid4()).upper()
    materials["speeds"].append({
        "curve_speed": None,
        "id": speed_normal_id,
        "mode": 0,
        "speed": 1.0,
        "type": "speed"
    })

    # Audio material
    audio_mat_id = str(uuid.uuid4()).upper()
    materials["audios"].append({
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "duration": total_duration_us,
        "id": audio_mat_id,
        "music_id": str(uuid.uuid4()),
        "name": os.path.basename(audio_path),
        "path": audio_path,
        "source_platform": 0,
        "type": "extract_music",
        "wave_points": []
    })

    # Video materials & track segments
    video_track_segments = []
    path_to_mat_id = {}

    for c in selected_clips:
        p = c["path"]
        if p not in path_to_mat_id:
            v_id = str(uuid.uuid4()).upper()
            path_to_mat_id[p] = v_id
            materials["videos"].append({
                "aigc_type": "none",
                "audio_fade": None,
                "category_id": "",
                "category_name": "local",
                "check_flag": 63487,
                "crop": {"lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0, "upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0},
                "crop_ratio": "free",
                "crop_scale": 1.0,
                "duration": c["duration"],
                "extra_type_option": 0,
                "formula_id": "",
                "freeze": None,
                "gameplay": None,
                "has_audio": False,
                "height": c["height"],
                "id": v_id,
                "intensifies_audio_path": "",
                "intensifies_path": "",
                "is_ai_generate_content": False,
                "is_unified_beauty_mode": False,
                "local_id": "",
                "local_material_id": "",
                "material_id": "",
                "material_name": os.path.basename(p),
                "material_url": "",
                "matting": {"flag": 0, "has_handled": False, "interactive_matting": None, "path": "", "strokes": []},
                "media_path": "",
                "object_locked": None,
                "path": p,
                "reverse_intensifies_path": "",
                "reverse_path": "",
                "type": "video",
                "width": c["width"]
            })
        else:
            v_id = path_to_mat_id[p]

        # Segment
        seg_id = str(uuid.uuid4()).upper()
        video_track_segments.append({
            "caption_info": None,
            "cartoon": False,
            "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False}, "rotation": 0.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}},
            "common_keyframes": [],
            "enable_adjust": True,
            "enable_color_curves": True,
            "enable_color_match_adjust": False,
            "enable_color_wheels": True,
            "enable_hsl": True,
            "enable_hsl_curves": True,
            "enable_lut": True,
            "enable_smart_color_adjust": False,
            "extra_material_refs": [],
            "group_id": "",
            "hdr_settings": None,
            "id": seg_id,
            "intensifies_audio": False,
            "is_loop": False,
            "is_placeholder": False,
            "is_tone_modify": False,
            "keyframe_refs": [],
            "last_nonzero_volume": 1.0,
            "material_id": v_id,
            "render_index": 0,
            "render_timerange": {"duration": 0, "start": 0},
            "reverse": False,
            "source_timerange": {"duration": c["duration"], "start": c["source_start"]},
            "speed": 1.0,
            "speed_id": speed_normal_id,
            "state": 0,
            "target_timerange": {"duration": c["duration"], "start": c["timeline_start"]},
            "track_attribute": 0,
            "track_render_index": 0,
            "uniform_scale": None,
            "visible": True,
            "volume": 0.0 # Tắt tiếng video nền để giọng đọc rõ ràng 100%
        })

    # Audio Segment
    audio_seg_id = str(uuid.uuid4()).upper()
    audio_track_segments = [{
        "caption_info": None,
        "cartoon": False,
        "clip": None,
        "common_keyframes": [],
        "enable_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "id": audio_seg_id,
        "intensifies_audio": False,
        "is_loop": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": audio_mat_id,
        "render_index": 0,
        "render_timerange": {"duration": 0, "start": 0},
        "reverse": False,
        "source_timerange": {"duration": total_duration_us, "start": 0},
        "speed": 1.0,
        "speed_id": speed_normal_id,
        "state": 0,
        "target_timerange": {"duration": total_duration_us, "start": 0},
        "track_attribute": 0,
        "track_render_index": 1,
        "uniform_scale": None,
        "visible": True,
        "volume": 1.0
    }]

    # 2. Tracks
    tracks = [
        {
            "attribute": 0,
            "flag": 0,
            "id": str(uuid.uuid4()).upper(),
            "is_default_name": True,
            "name": "Video Track",
            "segments": video_track_segments,
            "type": "video"
        },
        {
            "attribute": 0,
            "flag": 0,
            "id": str(uuid.uuid4()).upper(),
            "is_default_name": True,
            "name": "Audio Track",
            "segments": audio_track_segments,
            "type": "audio"
        }
    ]

    # 3. draft_content.json
    draft_content = {
        "canvas_config": {"background": None, "height": 1920, "ratio": "9:16", "width": 1080},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "voice_change_sync": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": now_us,
        "duration": total_duration_us,
        "extra_info": None,
        "fps": 30.0,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": draft_id,
        "is_drop_frame_timecode": False,
        "keyframe_graph_list": [],
        "keyframes": {"adjusts": [], "audios": [], "effects": [], "filters": [], "handwrites": [], "stickers": [], "texts": [], "videos": []},
        "last_modified_platform": {"app_id": 3704, "app_source": "capcut", "app_version": "164.0.0", "device_id": "", "hard_disk_id": "", "mac_address": "", "os": "windows", "os_version": "10.0.22631"},
        "materials": materials,
        "mixed_track_mode_on": False,
        "mutable_config": None,
        "name": display_name,
        "new_version": "164.0.0",
        "path": os.path.join(draft_dir, "draft_content.json").replace("\\", "/"),
        "platform": {"app_id": 3704, "app_source": "capcut", "app_version": "164.0.0", "device_id": "", "hard_disk_id": "", "mac_address": "", "os": "windows", "os_version": "10.0.22631"},
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": tracks,
        "update_time": now_us,
        "version": 360000
    }

    content_file = os.path.join(draft_dir, "draft_content.json")
    with open(content_file, "w", encoding="utf-8") as f:
        json.dump(draft_content, f, ensure_ascii=False, indent=2)

    # 4. draft_meta_info.json
    draft_meta = {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False,
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "",
        "draft_deeplink_url": "",
        "draft_enterprise_info": None,
        "draft_fold_path": draft_dir.replace("\\", "/"),
        "draft_id": draft_id,
        "draft_materials": [],
        "draft_name": display_name,
        "draft_new_version": "164.0.0",
        "draft_root_path": CAPCUT_DRAFT_ROOT.replace("\\", "/"),
        "draft_timeline_materials_size": 0,
        "draft_type": "",
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": total_duration_us
    }

    meta_file = os.path.join(draft_dir, "draft_meta_info.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(draft_meta, f, ensure_ascii=False, indent=2)

    # 5. Cập nhật root_meta_info.json
    root_meta_file = os.path.join(CAPCUT_DRAFT_ROOT, "root_meta_info.json")
    if os.path.exists(root_meta_file):
        try:
            with open(root_meta_file, "r", encoding="utf-8") as f:
                root_meta = json.load(f)
            
            draft_store = root_meta.get("all_draft_store", [])
            # Lọc bỏ bản ghi cũ cùng folder
            draft_store = [d for d in draft_store if d.get("draft_fold_path") != draft_dir.replace("\\", "/")]

            # Thêm bản ghi mới lên đầu danh sách để hiển thị đầu tiên trên CapCut
            draft_store.insert(0, {
                "cloud_draft_cover": False,
                "cloud_draft_sync": False,
                "draft_cloud_last_action_download": False,
                "draft_cloud_purchase_info": "",
                "draft_cloud_template_id": "",
                "draft_cloud_tutorial_info": "",
                "draft_cloud_videocut_purchase_info": "",
                "draft_cover": "",
                "draft_fold_path": draft_dir.replace("\\", "/"),
                "draft_id": draft_id,
                "draft_is_ai_shorts": False,
                "draft_is_cloud_temp_draft": False,
                "draft_is_infinite_canvas_draft": False,
                "draft_is_invisible": False,
                "draft_is_pippit_draft": False,
                "draft_is_web_article_video": False,
                "draft_json_file": content_file.replace("\\", "/"),
                "draft_name": display_name,
                "draft_new_version": "164.0.0",
                "draft_root_path": CAPCUT_DRAFT_ROOT.replace("\\", "/"),
                "draft_timeline_materials_size": 0,
                "draft_type": "",
                "draft_web_article_video_enter_from": "",
                "pippit_avatar_url": "",
                "pippit_extra_info": "",
                "pippit_id": "",
                "pippit_user_name": "",
                "streaming_edit_draft_ready": True,
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_entry_id": 0,
                "tm_draft_cloud_modified": 0,
                "tm_draft_cloud_parent_entry_id": 0,
                "tm_draft_cloud_space_id": 0,
                "tm_draft_cloud_user_id": 0,
                "tm_draft_create": now_us,
                "tm_draft_modified": now_us,
                "tm_draft_removed": 0,
                "tm_duration": total_duration_us
            })
            root_meta["all_draft_store"] = draft_store

            with open(root_meta_file, "w", encoding="utf-8") as f:
                json.dump(root_meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi cập nhật root_meta_info.json: {e}")

    return {
        "success": True,
        "draft_id": draft_id,
        "draft_name": display_name,
        "draft_dir": draft_dir,
        "clips_count": len(selected_clips),
        "duration_sec": audio_dur_sec
    }
