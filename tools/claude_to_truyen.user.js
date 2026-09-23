// ==UserScript==
// @name         Claude to Truyen Auto Producer (2-Skill Automation)
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Tự động hóa 2 Skill Claude (Tạo Kịch Bản + Gợi Ý Tiêu Đề/Thumb) và bắn dữ liệu về xưởng tại localhost:8888
// @author       Antigravity
// @match        https://claude.ai/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    const SERVER_URL = 'http://localhost:8888';
    let isAutoRunning = false;

    // Helper sleep
    const sleep = (ms) => new Promise(res => setTimeout(res, ms));

    // Helper gọi API
    async function apiFetch(endpoint, options = {}) {
        const url = `${SERVER_URL}${endpoint}`;
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: options.method || 'GET',
                url: url,
                headers: options.headers || { 'Content-Type': 'application/json' },
                data: options.body || null,
                onload: (response) => {
                    try {
                        resolve(JSON.parse(response.responseText));
                    } catch (e) {
                        resolve(response.responseText);
                    }
                },
                onerror: (err) => reject(err)
            });
        });
    }

    // Lấy ô nhập liệu ProseMirror của Claude
    function getChatInput() {
        return document.querySelector('div.ProseMirror[contenteditable="true"]') ||
               document.querySelector('div[contenteditable="true"]');
    }

    // Lấy nút Send của Claude
    function getSendButton() {
        return document.querySelector('button[aria-label="Send message"], button[aria-label="Send Message"]') ||
               document.querySelector('button.bg-text-000, button[type="submit"]');
    }

    // Kiểm tra Claude có đang trả lời không
    function isClaudeStreaming() {
        // Nút stop đang hiện hoặc streaming attribute
        const stopBtn = document.querySelector('button[aria-label="Stop Response"], button[aria-label="Stop response"], button[aria-label="Dừng câu trả lời"]');
        const streamingEl = document.querySelector('[data-is-streaming="true"]');
        return !!(stopBtn || streamingEl);
    }

    // Chờ Claude hoàn thành câu trả lời
    async function waitForClaudeDone(maxWaitSeconds = 180) {
        await sleep(2500); // Chờ khởi động streaming
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            if (!isClaudeStreaming()) {
                // Kiểm tra xem nút send đã hoạt động trở lại chưa
                await sleep(1500);
                if (!isClaudeStreaming()) return true;
            }
            await sleep(1000);
        }
        return false;
    }

    // Nhập text vào khung chat Claude một cách an toàn
    async function typeIntoChat(text) {
        const input = getChatInput();
        if (!input) throw new Error("Không tìm thấy khung chat Claude!");

        input.focus();
        // Xóa nội dung cũ
        input.innerHTML = '';
        // Chèn nội dung mới
        document.execCommand('insertText', false, text);
        
        // Dispatch các sự kiện input
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(500);
    }

    // Bấm gửi tin nhắn
    async function clickSend() {
        const btn = getSendButton();
        if (btn && !btn.disabled) {
            btn.click();
            return true;
        }
        // Fallback: bấm Enter
        const input = getChatInput();
        if (input) {
            input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
            return true;
        }
        return false;
    }

    // Lấy các câu trả lời của Claude trong đoạn chat hiện tại
    function getClaudeResponses() {
        const messages = Array.from(document.querySelectorAll('.font-claude-message, [data-is-streaming="false"], .grid-cols-1 .whitespace-pre-wrap'));
        return messages.map(m => m.innerText.trim()).filter(t => t.length > 0);
    }

    // Quy trình tự động 2 Skill cho 1 kịch bản thô
    async function runTwoSkillPipeline(project) {
        if (isAutoRunning) return;
        isAutoRunning = true;
        updateStatusWidget(`⏳ Đang xử lý [${project.id}]...`, "#eab308");

        try {
            // 1. Lấy cấu hình skill
            const skillConfig = await apiFetch('/api/claude-skill-config').catch(() => ({
                script_skill_command: '/tao-kich-ban',
                title_thumb_skill_command: '/tieu-de-thumb'
            }));

            const scriptSkill = (skillConfig.script_skill_command || '/tao-kich-ban').trim();
            const titleThumbSkill = (skillConfig.title_thumb_skill_command || '/tieu-de-thumb').trim();

            const rawContent = project.raw_content || project.content || "";
            if (!rawContent) throw new Error(`Kịch bản ${project.id} không có nội dung thô!`);

            // 2. LƯỢT 1: Gửi Skill Kịch Bản + Bản Thô
            updateStatusWidget(`[1/2] Đang viết kịch bản [${project.id}]...`, "#8b5cf6");
            const prompt1 = `${scriptSkill}\n\n${rawContent}`;
            await typeIntoChat(prompt1);
            await sleep(600);
            await clickSend();

            // Chờ Claude viết xong kịch bản
            const done1 = await waitForClaudeDone(240);
            if (!done1) throw new Error("Claude xử lý kịch bản quá lâu hoặc bị lỗi!");

            // 3. LƯỢT 2: Gửi Skill Gợi Ý Tiêu Đề & Thumbnail
            updateStatusWidget(`[2/2] Đang xin Tiêu đề & Thumb [${project.id}]...`, "#3b82f6");
            await sleep(1500);
            const prompt2 = `${titleThumbSkill}\n\nHãy gợi ý 3 tiêu đề hấp dẫn và 1 đoạn prompt mô tả ảnh thumbnail (tiếng Anh và tiếng Việt) cho kịch bản vừa tạo ở trên.`;
            await typeIntoChat(prompt2);
            await sleep(600);
            await clickSend();

            // Chờ Claude phản hồi lượt 2
            const done2 = await waitForClaudeDone(120);
            if (!done2) throw new Error("Claude sinh tiêu đề quá lâu!");

            // 4. Bóc tách kết quả
            const responses = getClaudeResponses();
            const fullScript = responses[responses.length - 2] || responses[0] || "";
            const titleThumbText = responses[responses.length - 1] || "";

            // Trích xuất tiêu đề hay nhất
            let title = project.title || "";
            const titleLines = titleThumbText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
            for (const line of titleLines) {
                if (line.match(/(tiêu đề|title|1\.|-)/i) && line.length > 10 && line.length < 120) {
                    title = line.replace(/^(tiêu đề|title|1\.|2\.|3\.|-|\*|\"|\:)+/i, '').replace(/[\"\*]/g, '').trim();
                    if (title.length > 10) break;
                }
            }
            if (!title || title.startsWith("Bản thô:")) {
                title = titleLines[0] ? titleLines[0].substring(0, 70) : `Kịch bản ${project.id}`;
            }

            // Gửi dữ liệu về xưởng
            updateStatusWidget(`💾 Đang lưu [${project.id}] về Xưởng...`, "#6366f1");
            const saveRes = await apiFetch(`/api/projects/${project.id}/ai-complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    content: fullScript,
                    thumb_prompt: titleThumbText,
                    notes: `Claude AI 2-Skill hoàn tất tự động`
                })
            });

            updateStatusWidget(`✅ Đã xong [${project.id}]!`, "#22c55e");
            setTimeout(refreshPendingList, 3000);

        } catch (err) {
            console.error("Lỗi 2-Skill Pipeline:", err);
            updateStatusWidget(`❌ Lỗi: ${err.message}`, "#ef4444");
        } finally {
            isAutoRunning = false;
        }
    }

    // Floating UI Widget
    let statusWidget = null;
    function createFloatingWidget() {
        if (statusWidget) return;
        statusWidget = document.createElement('div');
        statusWidget.id = 'truyen-automation-widget';
        statusWidget.style.cssText = `
            position: fixed;
            top: 15px;
            right: 80px;
            z-index: 999999;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 8px 14px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
            color: #1e293b;
        `;

        statusWidget.innerHTML = `
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #22c55e;" id="truyen-dot"></span>
                <span id="truyen-status-text" style="font-weight: 600;">Xưởng Video: Sẵn Sàng</span>
            </div>
            <button id="truyen-run-btn" style="
                background: #7c3aed;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 4px;
                transition: all 0.2s;
            ">⚡ Chạy Bản Thô Tiếp Theo</button>
        `;

        document.body.appendChild(statusWidget);

        document.getElementById('truyen-run-btn').onclick = async () => {
            try {
                const pending = await apiFetch('/api/projects/pending-raw');
                if (!pending || pending.length === 0) {
                    alert("Không có kịch bản thô nào đang chờ xử lý!");
                    return;
                }
                const first = pending[0];
                if (confirm(`Chạy 2-Skill tự động cho kịch bản [${first.id}]: "${first.title}"?`)) {
                    runTwoSkillPipeline(first);
                }
            } catch (err) {
                alert("Không kết nối được với Xưởng (localhost:8888). Vui lòng đảm bảo run_system.bat đang chạy!");
            }
        };
    }

    function updateStatusWidget(text, dotColor = "#22c55e") {
        createFloatingWidget();
        const t = document.getElementById('truyen-status-text');
        const d = document.getElementById('truyen-dot');
        if (t) t.innerText = text;
        if (d) d.style.background = dotColor;
    }

    async function refreshPendingList() {
        try {
            const pending = await apiFetch('/api/projects/pending-raw');
            const count = pending ? pending.length : 0;
            updateStatusWidget(`Xưởng Video (Chờ: ${count} bản thô)`, count > 0 ? "#8b5cf6" : "#22c55e");
        } catch (e) {
            updateStatusWidget("Xưởng Video (Chưa bật Server)", "#94a3b8");
        }
    }

    // Thêm nút lưu thủ công cho từng tin nhắn
    function addManualSaveButtons() {
        const messages = document.querySelectorAll('.font-claude-message, [data-is-streaming="false"]');
        messages.forEach((msg) => {
            if (msg.dataset.truyenSavedBtn) return;
            msg.dataset.truyenSavedBtn = "true";

            const btn = document.createElement('button');
            btn.innerHTML = '📥 Lưu vào Xưởng';
            btn.style.cssText = `
                margin-top: 8px;
                padding: 4px 10px;
                background-color: #f1f5f9;
                color: #475569;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s ease;
            `;

            btn.onclick = async () => {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang lưu...';
                const content = msg.innerText.trim();
                const lines = content.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                let title = lines[0] ? lines[0].replace(/^[#*-.\s]+/, '') : "Kịch bản Claude";
                if (title.length > 60) title = title.substring(0, 60) + "...";

                try {
                    const data = await apiFetch('/api/save-script', {
                        method: 'POST',
                        body: JSON.stringify({ title: title, content: content })
                    });
                    if (data.success) {
                        btn.innerHTML = `✅ Đã lưu [${data.id}]`;
                        btn.style.backgroundColor = '#dcfce7';
                        btn.style.color = '#15803d';
                    }
                } catch (err) {
                    btn.innerHTML = '❌ Lỗi lưu';
                    btn.disabled = false;
                }
            };
            msg.appendChild(btn);
        });
    }

    // Khởi tạo
    setTimeout(() => {
        createFloatingWidget();
        refreshPendingList();
        setInterval(refreshPendingList, 15000);
        setInterval(addManualSaveButtons, 2500);
    }, 2000);

})();
