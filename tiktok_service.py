# -*- coding: utf-8 -*-
"""
TikTok Service: Management of TikTok upload pipeline, caption templates,
account routing (Kenh Le / Kenh Chan), and automated scheduling at 12:00 & 20:00.
"""
import os
import sys
import json
import time
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import database
import task_logger

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ATP_TIKTOK_DIR = r"E:\myProject\atp_tt" if os.path.exists(r"E:\myProject\atp_tt") else r"D:\myProject\atp_tt"
ATP_PYTHON = os.path.join(ATP_TIKTOK_DIR, ".venv", "Scripts", "python.exe")
ATP_CLI = os.path.join(ATP_TIKTOK_DIR, "cli.py")

DEFAULT_TIKTOK_CONFIG = {
    "caption_template": "Rái Cá Audio số : {episode}",
    "hashtags": "#truyenhay #audiobook #xuhuong #reviewtruyen",
    "videos_per_day": 3,
    "schedule_times": ["08:00", "12:00", "20:00"],
    "auto_schedule_enabled": True,
    "visibility": 0  # 0: Public (Công khai), 1: Private (Riêng tư)
}

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_lock = threading.Lock()
_upload_lock = threading.Lock()
_active_uploading_ids = set()
_last_posted_slot: Optional[str] = None  # Format: "YYYY-MM-DD_HH"
_bulk_abort_requested = False

def abort_bulk_schedule():
    global _bulk_abort_requested
    _bulk_abort_requested = True

def get_tiktok_config() -> Dict[str, Any]:
    cfg = DEFAULT_TIKTOK_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "tiktok_config" in data and isinstance(data["tiktok_config"], dict):
                    cfg.update(data["tiktok_config"])
        except Exception as e:
            print(f"[TikTokService] Lỗi đọc config: {e}")
    cfg["posted_today_total"] = count_posted_today()
    cfg["posted_today_le"] = count_posted_today("kenh_le")
    cfg["posted_today_chan"] = count_posted_today("kenh_chan")
    return cfg

def save_tiktok_config(new_cfg: Dict[str, Any]) -> Dict[str, Any]:
    current_full = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current_full = json.load(f)
        except Exception:
            current_full = {}

    current_tt = current_full.get("tiktok_config", DEFAULT_TIKTOK_CONFIG.copy())
    current_tt.update(new_cfg)
    current_full["tiktok_config"] = current_tt

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current_full, f, ensure_ascii=False, indent=2)

    return current_tt

def resolve_target_channel(project: Dict[str, Any]) -> str:
    """Xác định kênh đăng (kenh_le hoặc kenh_chan) dựa trên số tập hoặc mã KB"""
    ep = project.get("ytb_episode")
    if ep is not None:
        try:
            return "kenh_chan" if int(ep) % 2 == 0 else "kenh_le"
        except Exception:
            pass

    # Nếu chưa cấp số tập, căn cứ vào số thứ tự của mã KBxxx
    pid = project.get("id", "")
    digits = "".join(filter(str.isdigit, pid))
    if digits:
        try:
            return "kenh_chan" if int(digits) % 2 == 0 else "kenh_le"
        except Exception:
            pass

    return "kenh_le"

def build_project_caption(project: Dict[str, Any], custom_hashtags: Optional[str] = None) -> str:
    """Tạo caption chuẩn theo template cấu hình: Rái Cá Audio số : {episode}"""
    cfg = get_tiktok_config()
    template = cfg.get("caption_template", "Rái Cá Audio số : {episode}").strip()
    
    ep = project.get("ytb_episode")
    if ep is None:
        pid = project.get("id", "")
        digits = "".join(filter(str.isdigit, pid)).lstrip("0")
        ep = digits if digits else "1"

    title = project.get("title", "").strip()
    hashtags = (custom_hashtags if custom_hashtags is not None else cfg.get("hashtags", "")).strip()

    # Thay thế các biến trong template
    caption = template.replace("{episode}", str(ep)).replace("{title}", title)
    
    if "{hashtags}" in template:
        caption = template.replace("{hashtags}", hashtags)
    elif hashtags:
        caption = f"{caption} {hashtags}".strip()

    # Giới hạn an toàn của TikTok (dưới 2000 ký tự)
    if len(caption) > 2000:
        caption = caption[:1990] + "..."
    return caption

def upload_project_tiktok(
    project_id: str,
    account: Optional[str] = None,
    caption: Optional[str] = None,
    visibility: Optional[int] = None,
    schedule_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """Thực hiện đăng tải hoặc lên lịch 1 video lên TikTok qua autotok CLI"""
    global _active_uploading_ids
    _active_uploading_ids.add(project_id)
    try:
        with _upload_lock:
            proj = database.get_project(project_id)
            if not proj:
                raise ValueError(f"Không tìm thấy kịch bản [{project_id}]")

            video_path = proj.get("video_tiktok_path")
            if not video_path or not os.path.exists(video_path):
                pkg_dir = database.get_package_dir(project_id)
                candidate = os.path.join(pkg_dir, f"{project_id}_tiktok.mp4")
                if os.path.exists(candidate):
                    video_path = candidate
                else:
                    raise ValueError(f"Kịch bản [{project_id}] chưa có video TikTok 9:16! Hãy tạo video TikTok trước.")

            target_acc = account or resolve_target_channel(proj)
            target_caption = caption if caption is not None else build_project_caption(proj)
            
            cfg = get_tiktok_config()
            vis = visibility if visibility is not None else cfg.get("visibility", 0)

            acc_display = "Kênh Số Lẻ (kenh_le)" if target_acc == "kenh_le" else "Kênh Số Chẵn (kenh_chan)" if target_acc == "kenh_chan" else target_acc
            mode_display = "Riêng tư (Private)" if vis == 1 else "Công khai (Public)"

            python_exe = ATP_PYTHON if os.path.exists(ATP_PYTHON) else sys.executable
            cmd = [
                python_exe,
                "-m", "autotok.cli",
                "upload",
                "-u", target_acc,
                "-v", video_path,
                "-t", target_caption,
                "-vi", str(vis)
            ]

            is_scheduled = False
            publish_time_display = ""
            if schedule_seconds and schedule_seconds >= 900:
                cmd.extend(["-sc", str(schedule_seconds)])
                is_scheduled = True
                sched_dt = datetime.now() + timedelta(seconds=schedule_seconds)
                publish_time_display = sched_dt.strftime("%H:%M ngày %d/%m/%Y")
                task_logger.add_log(
                    module="tiktok",
                    message=f"⏳ Đang tải và lên lịch đăng [{project_id}] lên {acc_display} vào {publish_time_display}...",
                    level="info",
                    project_id=project_id
                )
            else:
                task_logger.add_log(
                    module="tiktok",
                    message=f"🚀 Bắt đầu đăng ngay [{project_id}] lên {acc_display} [{mode_display}]...",
                    level="info",
                    project_id=project_id
                )

            env = os.environ.copy()
            env["AUTOTOK_BROWSER_CHANNEL"] = "chrome"

            res = subprocess.run(cmd, cwd=ATP_TIKTOK_DIR, env=env, capture_output=True, text=True, encoding="utf-8")
            
            if res.returncode != 0:
                err_msg = res.stderr.strip() or res.stdout.strip() or "Lỗi không xác định khi upload"
                task_logger.add_log(
                    module="tiktok",
                    message=f"❌ Thao tác TikTok thất bại cho [{project_id}]: {err_msg}",
                    level="error",
                    project_id=project_id
                )
                raise RuntimeError(err_msg)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            posted_timestamp = (datetime.now() + timedelta(seconds=schedule_seconds)).strftime("%Y-%m-%d %H:%M:%S") if is_scheduled else now_str

            database.update_project(
                project_id,
                tiktok_posted=1,
                tiktok_posted_at=posted_timestamp,
                tiktok_account=target_acc
            )

            if is_scheduled:
                task_logger.add_log(
                    module="tiktok",
                    message=f"✅ ĐÃ LÊN LỊCH TIKTOK CLOUD THÀNH CÔNG [{project_id}] vào {publish_time_display}! (Tắt máy vẫn đăng)",
                    level="success",
                    project_id=project_id
                )
            else:
                task_logger.add_log(
                    module="tiktok",
                    message=f"✅ ĐÃ ĐĂNG THÀNH CÔNG [{project_id}] lên {acc_display}! Caption: \"{target_caption[:50]}...\"",
                    level="success",
                    project_id=project_id
                )

            return {
                "success": True,
                "project_id": project_id,
                "account": target_acc,
                "caption": target_caption,
                "visibility": vis,
                "posted_at": posted_timestamp,
                "is_scheduled": is_scheduled,
                "scheduled_for": publish_time_display if is_scheduled else None
            }
    finally:
        _active_uploading_ids.discard(project_id)

def count_posted_today(account: Optional[str] = None) -> int:
    """Đếm số video TikTok đã đăng thành công trong ngày hôm nay cho kênh chỉ định (hoặc tổng cả 2 kênh)"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    projects = database.get_all_projects()
    count = 0
    for p in projects:
        posted_at = p.get("tiktok_posted_at")
        if posted_at and posted_at.startswith(today_str) and p.get("tiktok_posted"):
            if account:
                if p.get("tiktok_account") == account:
                    count += 1
            else:
                count += 1
    return count

def is_slot_posted_today(target_hour: int, account: Optional[str] = None) -> bool:
    """Kiểm tra khung giờ target_hour của ngày hôm nay đã có video đăng cho kênh account chưa"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    projects = database.get_all_projects()
    for p in projects:
        posted_at = p.get("tiktok_posted_at")
        if posted_at and posted_at.startswith(today_str) and p.get("tiktok_posted"):
            if account and p.get("tiktok_account") != account:
                continue
            try:
                hour_part = int(posted_at.split()[1].split(":")[0])
                if hour_part == target_hour:
                    return True
            except Exception:
                pass
    return False

def calculate_schedule_slots_for_channel(candidate_count: int, channel: str) -> List[Dict[str, Any]]:
    """Tính toán các mốc thời gian phát hành RIÊNG BIỆT CHO MỖI KÊNH (mỗi kênh videos_per_day video/ngày)"""
    from datetime import datetime, timedelta
    cfg = get_tiktok_config()
    times = cfg.get("schedule_times", ["08:00", "12:00", "20:00"])
    if not times:
        times = ["08:00", "12:00", "20:00"]
    max_per_day = int(cfg.get("videos_per_day", 3))

    parsed_times = []
    for t in times:
        try:
            parts = t.strip().split(":")
            h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            parsed_times.append((h, m))
        except Exception:
            pass
    if not parsed_times:
        parsed_times = [(8, 0), (12, 0), (20, 0)]
    parsed_times.sort()

    now = datetime.now()
    slots = []
    cur_day = now.date()

    # Kiểm tra số lượng video mà KÊNH NÀY đã đăng hôm nay
    posted_today_channel = count_posted_today(channel)
    remaining_today = max(0, max_per_day - posted_today_channel)

    days_checked = 0
    while len(slots) < candidate_count and days_checked < 60:
        daily_slots_limit = remaining_today if days_checked == 0 else max_per_day
        slots_added_today = 0

        for h, m in parsed_times:
            if slots_added_today >= daily_slots_limit:
                break
            slot_dt = datetime.combine(cur_day, datetime.min.time()).replace(hour=h, minute=m)
            diff_sec = int((slot_dt - now).total_seconds())
            if diff_sec >= 960:  # Ít nhất 16 phút để trừ hao thời gian upload
                slots.append({
                    "delay_seconds": diff_sec,
                    "display": slot_dt.strftime("%H:%M ngày %d/%m/%Y"),
                    "date_str": slot_dt.strftime("%Y-%m-%d"),
                    "time_str": f"{h:02d}:{m:02d}"
                })
                slots_added_today += 1
                if len(slots) >= candidate_count:
                    break
        cur_day += timedelta(days=1)
        days_checked += 1

    return slots

def calculate_schedule_slots(candidate_count: int) -> List[Dict[str, Any]]:
    """Tương thích ngược: tính slot chung cho danh sách kịch bản"""
    return calculate_schedule_slots_for_channel(candidate_count, "kenh_le")

def get_next_scheduled_candidates() -> List[Dict[str, Any]]:
    """Lấy danh sách các kịch bản sẵn sàng đăng và gán mốc giờ phát hành RIÊNG BIỆT CHO TỪNG KÊNH"""
    projects = database.get_all_projects()
    raw_candidates = []
    for p in projects:
        if p.get("id") in _active_uploading_ids:
            continue
        if not p.get("tiktok_posted"):
            v_path = p.get("video_tiktok_path")
            if not v_path or not os.path.exists(v_path):
                pkg_dir = database.get_package_dir(p["id"])
                cand = os.path.join(pkg_dir, f"{p['id']}_tiktok.mp4")
                if os.path.exists(cand):
                    v_path = cand

            if v_path and os.path.exists(v_path):
                target_acc = resolve_target_channel(p)
                raw_candidates.append({
                    "id": p["id"],
                    "title": p.get("title", ""),
                    "episode": p.get("ytb_episode"),
                    "account": target_acc,
                    "account_label": "Kênh Số Lẻ" if target_acc == "kenh_le" else "Kênh Số Chẵn",
                    "caption": build_project_caption(p),
                    "video_path": v_path
                })

    # Tách 2 kênh riêng biệt
    le_cands = [c for c in raw_candidates if c["account"] == "kenh_le"]
    chan_cands = [c for c in raw_candidates if c["account"] == "kenh_chan"]

    # Sắp xếp số tập tăng dần cho từng kênh
    le_cands.sort(key=lambda x: x["episode"] if x["episode"] is not None else 999999)
    chan_cands.sort(key=lambda x: x["episode"] if x["episode"] is not None else 999999)

    # Gán các slot thời gian ĐỘC LẬP CHO TỪNG KÊNH (Mỗi kênh đủ videos_per_day video/ngày)
    le_slots = calculate_schedule_slots_for_channel(len(le_cands), "kenh_le")
    for i, c in enumerate(le_cands):
        c["scheduled_slot"] = le_slots[i] if i < len(le_slots) else None

    chan_slots = calculate_schedule_slots_for_channel(len(chan_cands), "kenh_chan")
    for i, c in enumerate(chan_cands):
        c["scheduled_slot"] = chan_slots[i] if i < len(chan_slots) else None

    # Hợp nhất và sắp xếp theo thứ tự số tập tăng dần
    all_candidates = le_cands + chan_cands
    all_candidates.sort(key=lambda x: x["episode"] if x["episode"] is not None else 999999)
    return all_candidates

def bulk_schedule_tiktok(limit: Optional[int] = None, project_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tải và lên lịch hàng loạt video thẳng lên máy chủ TikTok Cloud (mỗi kênh N video/ngày)"""
    candidates = get_next_scheduled_candidates()
    if not candidates:
        return {"success": False, "message": "Không có video TikTok nào đang chờ trong hàng đợi."}

    if project_ids:
        pid_set = set(project_ids)
        candidates = [c for c in candidates if c["id"] in pid_set]
        if not candidates:
            return {"success": False, "message": "Không có video nào trong danh sách đã chọn sẵn sàng đăng TikTok."}
        
        # Tái tính slot độc lập cho tập con đã chọn
        le_subset = [c for c in candidates if c["account"] == "kenh_le"]
        chan_subset = [c for c in candidates if c["account"] == "kenh_chan"]
        le_slots = calculate_schedule_slots_for_channel(len(le_subset), "kenh_le")
        for i, c in enumerate(le_subset):
            c["scheduled_slot"] = le_slots[i] if i < len(le_slots) else None
        chan_slots = calculate_schedule_slots_for_channel(len(chan_subset), "kenh_chan")
        for i, c in enumerate(chan_subset):
            c["scheduled_slot"] = chan_slots[i] if i < len(chan_slots) else None

    if limit and limit > 0:
        candidates = candidates[:limit]

    results = []
    task_logger.add_log(
        module="tiktok",
        message=f"🚀 Bắt đầu lên lịch hàng loạt {len(candidates)} video lên TikTok Cloud...",
        level="info"
    )

    global _bulk_abort_requested
    _bulk_abort_requested = False
    consecutive_errors = 0
    for c in candidates:
        if _bulk_abort_requested:
            task_logger.add_log(module="tiktok", message="🛑 Đã dừng lên lịch hàng loạt theo yêu cầu.", level="warning")
            break
        pid = c["id"]
        slot = c.get("scheduled_slot")
        if not slot:
            continue
        delay_sec = slot.get("delay_seconds")
        display_time = slot.get("display")

        try:
            res = upload_project_tiktok(
                project_id=pid,
                account=c.get("account"),
                caption=c.get("caption"),
                schedule_seconds=delay_sec
            )
            consecutive_errors = 0
            results.append({"id": pid, "status": "success", "scheduled_for": display_time, "account": c.get("account")})
        except Exception as e:
            consecutive_errors += 1
            results.append({"id": pid, "status": "error", "error": str(e), "account": c.get("account")})
            if consecutive_errors >= 2:
                task_logger.add_log(
                    module="tiktok",
                    message=f"⚠️ Đã tạm dừng lên lịch hàng loạt vì gặp lỗi lặp lại từ TikTok ({str(e)[:100]}).",
                    level="warning"
                )
                break

    return {"success": True, "total": len(candidates), "results": results}

def _scheduler_loop():
    """Vòng lặp ngầm kiểm tra lịch: Tự động đăng theo videos_per_day cho MỖI KÊNH và schedule_times"""
    global _last_posted_slot
    print("[TikTokScheduler] Khoi dong bo hen gio dang video TikTok!")

    while True:
        try:
            time.sleep(30)
            now = datetime.now()
            cfg = get_tiktok_config()

            if not cfg.get("auto_schedule_enabled", True):
                continue

            max_per_day = int(cfg.get("videos_per_day", 3))
            times = cfg.get("schedule_times", ["08:00", "12:00", "20:00"])
            cur_hour = now.hour
            cur_minute = now.minute

            is_matching_time = False
            target_slot_name = ""
            for t in times:
                try:
                    parts = t.strip().split(":")
                    th, tm = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
                    if cur_hour == th and 0 <= (cur_minute - tm) <= 10:
                        is_matching_time = True
                        target_slot_name = f"{th:02d}:{tm:02d}"
                        break
                except Exception:
                    pass

            if is_matching_time:
                # Kiểm tra lần lượt từng kênh độc lập: Mỗi kênh 3 video / ngày
                for target_acc in ["kenh_le", "kenh_chan"]:
                    acc_label = "Kênh Số Lẻ" if target_acc == "kenh_le" else "Kênh Số Chẵn"
                    posted_today = count_posted_today(target_acc)
                    if posted_today >= max_per_day:
                        continue

                    slot_key = f"{now.strftime('%Y-%m-%d')}_{target_acc}_{target_slot_name}"
                    if _last_posted_slot != slot_key and not is_slot_posted_today(cur_hour, target_acc):
                        candidates = [c for c in get_next_scheduled_candidates() if c.get("account") == target_acc]
                        if candidates:
                            target_proj = candidates[0]
                            pid = target_proj["id"]
                            task_logger.add_log(
                                module="tiktok",
                                message=f"⏰ [Hẹn Giờ {target_slot_name}] Đăng video {posted_today + 1}/{max_per_day} cho {acc_label}: [{pid}]...",
                                level="info",
                                project_id=pid
                            )
                            try:
                                upload_project_tiktok(pid)
                                _last_posted_slot = slot_key
                            except Exception as ex:
                                print(f"[TikTokScheduler] Lỗi đăng bài {pid} cho {acc_label}: {ex}")
                        else:
                            task_logger.add_log(
                                module="tiktok",
                                message=f"⏰ [Hẹn Giờ {target_slot_name}] Không có video TikTok dọc nào đang chờ cho {acc_label}.",
                                level="warning"
                            )
                            _last_posted_slot = slot_key
        except Exception as e:
            print(f"[TikTokScheduler] Ngoại lệ vòng lặp: {e}")
            time.sleep(10)

def start_scheduler():
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="TikTokAutoScheduler")
            _scheduler_thread.start()
