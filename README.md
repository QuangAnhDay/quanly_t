# Xưởng Sản Xuất Video Audio - Quản Lý Kịch Bản Bán Tự Động

Hệ thống bán tự động hóa quy trình sản xuất video truyện ngắn/dài cho TikTok, YouTube Shorts và Reels:
- **Quản lý đa Profile Chrome:** Mở đồng loạt các tài khoản Google đã cấu hình sẵn Skill kịch bản trên Claude.ai.
- **Thu thập kịch bản 1-Click:** Tiện ích Tampermonkey tự động gắn nút `[Lưu vào Xưởng Truyện]` trên web Claude, tự gán mã `KB001`, `KB002`...
- **Quản lý tiến trình thông minh (Web Dashboard):** Theo dõi tiến trình 4 giai đoạn trực quan: *Chờ duyệt/voice* $\rightarrow$ *Đã có Audio* $\rightarrow$ *Đã render video* $\rightarrow$ *Hoàn thành*.
- **Hỗ trợ cả VoiceStudio Local & Edge-TTS:** Tự động bắt file âm thanh xuất từ repo local, gán đường dẫn và cập nhật trạng thái.
- **Hỗ trợ CapCut & Render tự động (FFmpeg):** Tự động phát hiện video thành phẩm khi xuất từ CapCut.

---

## Cài đặt & Khởi động nhanh

1. **Cài đặt thư viện cần thiết:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Khởi chạy hệ thống 1-Click:**
   * Bấm đúp chuột vào file `run_system.bat`.
   * Web Dashboard sẽ tự động mở tại: `http://localhost:8888`.

3. **Cài đặt Userscript lưu kịch bản từ Claude:**
   * Mở tiện ích Tampermonkey trên Chrome.
   * Dán toàn bộ nội dung từ file `tools/claude_to_truyen.user.js` và bấm Lưu.

Xem hướng dẫn sử dụng chi tiết tại [HD_SU_DUNG.md](HD_SU_DUNG.md).
