# Hướng Dẫn Sử Dụng Xưởng Sản Xuất Video Truyện Bán Tự Động

Chào mừng bạn đến với hệ thống tự động hóa và quản lý kịch bản video truyện tại `C:\project\myProject\truyen`!

---

## 1. Khởi động hệ thống (1-Click)
Có 2 cách cực kỳ đơn giản để bật hệ thống:

* **Cách 1 (Từ Windows Explorer - Khuyên dùng):**
  1. Mở thư mục `C:\project\myProject\truyen` trên máy tính bằng Windows Explorer (hoặc nhấn phím `Windows + E`).
  2. Bấm đúp chuột vào file: **`run_system.bat`**.
  *(Lưu ý: Nếu bạn bấm chuột vào file `run_system.bat` ở cột cây thư mục bên trái trong VS Code/IDE, nó chỉ là mở tab để xem nội dung code chứ máy tính chưa chạy file. Bạn cần mở từ thư mục ngoài Windows).*

* **Cách 2 (Chạy ngay trong cửa sổ lập trình/IDE này):**
  1. Nhấn phím tắt **`Ctrl + ~`** (phím dấu ngã cạnh số 1) để mở Terminal phía dưới.
  2. Gõ lệnh sau rồi nhấn Enter:
     ```cmd
     .\run_system.bat
     ```

Hệ thống sẽ tự động:
1. Kích hoạt server và bộ theo dõi file ngầm (File Watcher).
2. Tự động bật trình duyệt web vào thẳng Web Dashboard tại: **`http://localhost:8888`**.
3. Sẵn sàng nhận kịch bản từ Claude và làm voice/video ngay lập tức!

---

## 2. Quy Trình Sử Dụng Hàng Ngày

### Bước 1: Mở 5 tài khoản Claude cùng lúc
* Trên thanh menu trên cùng của Web Dashboard, bấm nút màu cam: **`[Mở 5 Profile Claude]`** (hoặc chạy file `tools\launch_5_claude.bat`).
* 5 cửa sổ Chrome với 5 Profile Google sẽ mở ra song song, đã đăng nhập sẵn tài khoản và Skill của bạn.

### Bước 2: Tạo kịch bản & Lưu vào hệ thống
Bạn có 2 cách cực kỳ nhanh:
* **Cách A (1-Click từ Web Claude - Khuyên dùng):**
  1. Cài tiện ích **Tampermonkey** trên Chrome (nếu chưa có).
  2. Mở file `tools\claude_to_truyen.user.js` $\rightarrow$ Copy toàn bộ code $\rightarrow$ Tạo script mới trên Tampermonkey rồi dán vào $\rightarrow$ Bấm Save.
  3. Khi bạn prompt trên Claude xong, dưới câu trả lời sẽ có nút màu tím: **`[📥 Lưu vào Xưởng Truyện]`**.
  4. Bạn bấm 1 cái: Kịch bản tự bay vào Dashboard với mã `KB001`, `KB002`...
* **Cách B (Nhập trực tiếp trên Dashboard):**
  1. Bấm nút **`[+ Thêm Kịch Bản]`** ở góc phải trên Dashboard.
  2. Nhập Tiêu đề, dán Nội dung kịch bản và chọn giọng đọc $\rightarrow$ Bấm Lưu.

---

### Bước 3: Tạo giọng đọc (Audio)
Bạn có 2 lựa chọn theo sở thích:

#### Lựa chọn 1: Dùng Động cơ Giọng Đọc Nhanh (Edge-TTS)
* Ngay trên thẻ kịch bản trên Dashboard, bấm nút: **`[🎙️ Tạo Voice]`**.
* Chỉ mất **3 - 5 giây**, file âm thanh chất lượng cao tiếng Việt (giọng Hoài My hoặc Nam Minh) sẽ được tạo xong.
* Bạn có thể bấm nút **Play (▶️)** để nghe thử trực tiếp trên Dashboard.

#### Lựa chọn 2: Dùng VoiceStudio (chạy ở localhost)
* Bạn dán kịch bản vào VoiceStudio trên Edge và bấm Generate.
* Khi file render xong, Bộ theo dõi ngầm (`file_watcher.py`) sẽ **tự động bốc file mới nhất**, đổi tên thành `KBxxx.wav` và chuyển thẳng vào thư mục `2_audio_input`.
* Trạng thái trên Dashboard sẽ tự động nhảy sang: **`🟢 2. Đã có Audio`**.

---

### Bước 4: Dựng CapCut & Hoàn Thành
1. Mở CapCut PC lên.
2. Kéo file âm thanh từ thư mục `2_audio_input` (hoặc bấm nút "Mở Thư Mục Âm Thanh" trên Dashboard).
3. Thêm video nền của bạn, bật phụ đề tự động (Auto Captions) trong CapCut nếu muốn.
4. Khi bấm **Export** từ CapCut, lưu file thành phẩm vào thư mục:
   `C:\project\myProject\truyen\3_video_output\KB001.mp4`
5. Ngay khi file xuất hiện, Dashboard sẽ tự động cập nhật trạng thái sang: **`🟣 4. Hoàn Thành / Sẵn sàng đăng`**.

---

## 3. Cấu Trúc Thư Mục
```text
C:\project\myProject\truyen\
├── 1_scripts\           # Kịch bản text dự phòng (.txt)
├── 2_audio_input\       # Toàn bộ file voice hoàn chỉnh (KB001.mp3, KB002.mp3...)
├── 3_video_output\      # Video thành phẩm xuất từ CapCut (KB001.mp4...)
├── 4_thumbnails\        # Ảnh thumbnail
├── backgrounds\         # Kho video nền bạn tải về
├── data\                # Cơ sở dữ liệu SQLite
├── tools\               # Bộ công cụ (Launchers, Watcher, Userscript)
├── web\                 # Giao diện Web Dashboard
├── run_system.bat       # Nút bấm khởi động 1-Click
└── config.json          # File cấu hình đường dẫn
```
