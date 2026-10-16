# 🗺️ CODEBASE MAP - BẢN ĐỒ KIẾN TRÚC DỰ ÁN QUẢN LÝ TRUYỆN (QUANLY_TT)
> **Mục đích**: Tài liệu bản đồ định tuyến nhanh cho Agent / Developer. Khi mất context hoặc nhận task mới, chỉ cần tra cứu bản đồ này để biết chính xác file cần đọc/sửa, **KHÔNG CẦN** quét toàn bộ dự án.

---

## 1. Bản Đồ File & Trách Nhiệm (File-to-Role Matrix)

| File | Trách Nhiệm Chính | Các Hàm / Biến Quan Trọng | Khi Nào Cần Đọc/Sửa? |
| :--- | :--- | :--- | :--- |
| **`server.py`** | FastAPI Web Server (Port 8888). Tiếp nhận toàn bộ request từ giao diện Dashboard `web/index.html`. | `app`, các `@app.get / @app.post`, `get_config()`, `/api/system/health`, `/api/tiktok/*` | Khi thêm API mới, sửa giao thức trao đổi giữa Web UI và Backend. |
| **`database.py`** | Quản lý SQLite database (`data/truyen.db`), bảng `projects`. Migration & CRUD kịch bản. | `init_db()`, `get_project()`, `update_project()`, `get_all_projects()`, `toggle_tiktok_posted()` | Khi thêm trường dữ liệu mới vào kịch bản, sửa logic truy vấn, lưu trạng thái. |
| **`tiktok_service.py`** | Tự động hóa đăng tải & Lên lịch TikTok Cloud (`ATP_tiktok`), chia kênh chẵn/lẻ, template caption. | `upload_project_tiktok()`, `bulk_schedule_tiktok()`, `get_next_scheduled_candidates()`, `_scheduler_loop()` | Khi sửa logic đăng TikTok, định dạng caption `Rái Cá Audio`, hẹn giờ, tần suất video/ngày. |
| **`voicestudio_service.py`** | Kết nối & kiểm soát VoiceStudio API Server (Port 3900) chạy GPU clone giọng đọc. | `check_voicestudio_health()`, `ensure_voicestudio_running()`, `fetch_voice_list()` | Khi can thiệp logic kết nối VoiceStudio, cổng 3900, danh sách giọng clone. |
| **`audio_engine.py`** | Sinh audio giọng đọc từ text (hỗ trợ cả Edge-TTS và VoiceStudio clone). | `generate_audio()`, `generate_voicestudio_audio()` | Khi sửa chất lượng âm thanh, tốc độ đọc, định dạng wav/mp3. |
| **`bg_manager.py`** | Quản lý kho video nền (`backgrounds/` nau_an, handmade; doc & ngang). | `select_smart_background()`, `get_background_stats()` | Khi sửa logic chọn video nền ngẫu nhiên hoặc kiểm kê video nền. |
| **`capcut_engine.py`** | Can thiệp CapCut Draft root, tạo project CapCut tự động từ template. | `create_capcut_draft()`, `CAPCUT_DRAFT_ROOT` | Khi sửa cấu trúc timeline CapCut, phụ đề, hiệu ứng chuyển cảnh. |
| **`video_engine.py`** | Render video MP4 (16:9 YouTube & 9:16 TikTok) bằng FFmpeg. | `render_youtube_video()`, `render_tiktok_fast()` | Khi sửa độ phân giải, bitrate, crop video 15 phút đầu cho TikTok. |
| **`thumbnail_engine.py`** | Quản lý ảnh thumbnail, ghép prompt ảnh từ kho `thumb_assets/`. | `generate_thumbnail()`, `get_thumb_assets_count()` | Khi sửa logic tạo ảnh bìa YouTube, kích thước 1280x720. |
| **`affiliate_manager.py`** | Kho liên kết Shopee Affiliate, parse file Excel/Google Sheets, tạo comment ghim. | `load_affiliate_data()`, `batch_add_links()`, `render_affiliate_comment()` | Khi sửa tính năng Shopee Affiliate, import danh sách sản phẩm. |
| **`task_queue.py`** | Hàng đợi tiến trình chạy ngầm (Render video, tạo audio hàng loạt). | `add_task()`, `task_worker()` | Khi sửa tốc độ xử lý hàng đợi, giới hạn tác vụ song song. |
| **`task_logger.py`** | Hệ thống ghi nhật ký hoạt động thời gian thực (Activity Logs). | `add_log()`, `get_recent_logs()`, `clear_logs()` | Khi thêm log giám sát tiến độ hoặc thông báo lỗi cho người dùng. |
| **`web/index.html`** | Giao diện Single Page Application (Tailwind CSS, FontAwesome, JS thuần). | `fetchProjects()`, `updateHealthUI()`, `loadTikTokConfig()`, các Modal popup | Khi sửa giao diện, nút bấm, bảng hiển thị, font chữ, popup. |
| **`config.json`** | Cấu hình toàn cục (Port, Voice mặc định, Chrome profiles, TikTok config). | `tiktok_config`, `claude_skills`, `default_voice` | Khi xem hoặc đổi các tham số mặc định của hệ thống. |

---

## 2. Tra Cứu Nhanh Theo Task (Task-to-Files Lookup)

Khi nhận một task, chỉ cần mở đúng các file sau:

* **Task: Sửa/Thêm tính năng Đăng TikTok & Hẹn giờ**:
  $\rightarrow$ Đọc: `tiktok_service.py` $\rightarrow$ `server.py` $\rightarrow$ `web/index.html` (Modal `#tiktok-modal`).
* **Task: Sửa Voice / Âm thanh / VoiceStudio**:
  $\rightarrow$ Đọc: `voicestudio_service.py` $\rightarrow$ `audio_engine.py` $\rightarrow$ `server.py`.
* **Task: Sửa Video / Cắt ghép 9:16 TikTok / CapCut**:
  $\rightarrow$ Đọc: `video_engine.py` $\rightarrow$ `capcut_engine.py` $\rightarrow$ `bg_manager.py`.
* **Task: Sửa Kho Shopee Affiliate**:
  $\rightarrow$ Đọc: `affiliate_manager.py` $\rightarrow$ `server.py` $\rightarrow$ `web/index.html` (Modal `#affiliate-modal`).
* **Task: Sửa Bảng Kịch Bản / Trạng Thái / Cột Dữ Liệu**:
  $\rightarrow$ Đọc: `database.py` $\rightarrow$ `server.py` $\rightarrow$ `web/index.html` (Bảng chính `renderTable()`).
* **Task: Sửa Giám sát dung lượng ổ đĩa / Kho tài nguyên**:
  $\rightarrow$ Đọc: `server.py` (`/api/system/health`) $\rightarrow$ `web/index.html` (`updateHealthUI()`).

---

## 3. Luồng Dữ Liệu Cốt Lõi (Data Flow Pipelines)

```
1. SẢN XUẤT NỘI DUNG:
   [Prompt Claude/Thủ công] ──> server.py ──> database.py (Kịch bản thô)
                                     │
2. ÂM THANH & VIDEO 16:9:            ▼
   voicestudio_service.py (Port 3900) ──> audio_engine.py ──> audio.wav/mp3
                                                                   │
   bg_manager.py (Video nền ngang) ───────────────────────────────┤
                                                                   ▼
   capcut_engine.py / video_engine.py ──────────────> outputs/KBxxx/KBxxx.mp4 (16:9 YouTube)
                                                                   │
3. TRÍCH XUẤT TIKTOK 9:16:                                         ▼
   video_engine.py (Cắt 15p đầu, căn dọc 9:16) ──> outputs/KBxxx/KBxxx_tiktok.mp4
                                                                   │
4. PHÁT HÀNH TIKTOK:                                               ▼
   tiktok_service.py ──> ATP_tiktok (cli.py -u kenh_chan/le -sc delay_sec) ──> TikTok Cloud Server
```

---

## 4. Công Cụ MCP Codebase Memory (`codebase-memory-mcp`)
Dự án đã được index vào đồ thị tri thức của **`codebase-memory-mcp`**:
* Thư mục graph: `.codebase-memory/graph.db.zst`
* Các tool Agent có thể gọi trực tiếp:
  - `get_architecture`: Xem cấu trúc tầng và luồng phụ thuộc.
  - `trace_path`: Truy vết đường đi giữa 2 hàm / 2 file bất kỳ.
  - `search_graph`: Tìm kiếm quan hệ giữa các symbol.
