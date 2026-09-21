// ==UserScript==
// @name         Claude to Truyen Auto Saver (1-Click)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Tự động lưu kịch bản từ Claude.ai vào hệ thống quản lý tại localhost:8888
// @author       Antigravity
// @match        https://claude.ai/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    function addSaveButtons() {
        // Tìm các khung phản hồi của Claude
        const messages = document.querySelectorAll('.font-claude-message, [data-is-streaming="false"]');
        
        messages.forEach((msg) => {
            if (msg.dataset.truyenSavedBtn) return;
            msg.dataset.truyenSavedBtn = "true";

            const btn = document.createElement('button');
            btn.innerHTML = '📥 Lưu vào Xưởng Truyện';
            btn.style.cssText = `
                margin-top: 10px;
                padding: 6px 14px;
                background-color: #7c3aed;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
            `;

            btn.onmouseover = () => btn.style.backgroundColor = '#6d28d9';
            btn.onmouseout = () => btn.style.backgroundColor = '#7c3aed';

            btn.onclick = async () => {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang lưu...';

                const content = msg.innerText.trim();
                // Lấy dòng đầu tiên làm tiêu đề mặc định
                const lines = content.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                let title = lines[0] ? lines[0].replace(/^[#*-.\s]+/, '') : "Kịch bản Claude";
                if (title.length > 50) title = title.substring(0, 50) + "...";

                try {
                    const response = await fetch('http://localhost:8888/api/save-script', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: title,
                            content: content
                        })
                    });

                    const data = await response.json();
                    if (data.success) {
                        btn.innerHTML = `✅ Đã lưu [${data.id}]`;
                        btn.style.backgroundColor = '#16a34a';
                    } else {
                        btn.innerHTML = '❌ Lỗi lưu';
                        btn.disabled = false;
                    }
                } catch (err) {
                    console.error("Lỗi gửi kịch bản:", err);
                    btn.innerHTML = '❌ Không kết nối được Server (Cần chạy run_system.bat)';
                    btn.style.backgroundColor = '#dc2626';
                    btn.disabled = false;
                }
            };

            msg.appendChild(btn);
        });
    }

    const observer = new MutationObserver(addSaveButtons);
    observer.observe(document.body, { childList: true, subtree: true });
    setInterval(addSaveButtons, 2000);
})();
