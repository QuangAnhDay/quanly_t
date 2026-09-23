// ==UserScript==
// @name         Claude to Truyen Auto Producer (2-Skill Automation)
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Tự động hóa 2 Skill Claude (Tạo Kịch Bản + Gợi Ý Tiêu Đề/Thumb) và gửi dữ liệu về xưởng tại localhost:8888
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

    // Helper gọi API tới server
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
               document.querySelector('div[contenteditable="true"]') ||
               document.querySelector('fieldset div[contenteditable="true"]');
    }

    // Lấy nút Send của Claude
    function getSendButton() {
        return document.querySelector('button[aria-label*="Send"]') ||
               document.querySelector('button[aria-label*="Gửi"]') ||
               document.querySelector('button[type="submit"]') ||
               document.querySelector('button.bg-text-000') ||
               document.querySelector('fieldset button:last-child');
    }

    // Kiểm tra Claude có đang streaming/phản hồi không
    function isClaudeStreaming() {
        const stopBtn = document.querySelector('button[aria-label*="Stop"], button[aria-label*="Dừng"]');
        const streamingEl = document.querySelector('[data-is-streaming="true"]');
        return !!(stopBtn || streamingEl);
    }

    // Chờ phần tử xuất hiện trong DOM
    async function waitForElement(getterFn, maxWaitSeconds = 15) {
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            const el = getterFn();
            if (el) return el;
            await sleep(500);
        }
        return null;
    }

    // Chờ Claude hoàn thành câu trả lời
    async function waitForClaudeDone(maxWaitSeconds = 240) {
        await sleep(3000); // Chờ khởi động streaming
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            if (!isClaudeStreaming()) {
                await sleep(2000);
                if (!isClaudeStreaming()) return true;
            }
            await sleep(1000);
        }
        return false;
    }

    // Nhập text vào khung chat Claude một cách an toàn
    async function typeIntoChat(text) {
        const input = await waitForElement(getChatInput, 15);
        if (!input) throw new Error("Không tìm thấy khung chat Claude! Vui lòng tải lại trang.");

        input.focus();
        await sleep(300);

        // Bôi đen toàn bộ nếu có nội dung cũ
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(input);
        selection.removeAllRanges();
        selection.addRange(range);

        // Chèn nội dung text
        const inserted = document.execCommand('insertText', false, text);
        if (!inserted || !input.innerText.trim()) {
            input.innerHTML = `<p>${text.replace(/\n/g, '<br>')}</p>`;
        }
        
        // Dispatch các sự kiện cần thiết cho React / ProseMirror
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(600);
    }

    // Bấm gửi tin nhắn
    async function clickSend() {
        await sleep(300);
        const btn = getSendButton();
        if (btn && !btn.disabled) {
            btn.click();
            return true;
        }
        // Fallback: bấm Enter vào input
        const input = getChatInput();
        if (input) {
            input.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true
            }));
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
        updateStatusWidget(`⏳ Đang chạy kịch bản [${project.id}]...`, "#eab308");

        try {
            // 1. Lấy cấu hình skill từ server
            const skillConfig = await apiFetch('/api/claude-skill-config').catch(() => ({
                script_skill_command: '/tao-kich-ban',
                title_thumb_skill_command: '/tieu-de-thumb'
            }));

            const scriptSkill = (skillConfig.script_skill_command || '/tao-kich-ban').trim();
            const titleThumbSkill = (skillConfig.title_thumb_skill_command || '/tieu-de-thumb').trim();

            const rawContent = project.raw_content || project.content || "";
            if (!rawContent) throw new Error(`Kịch bản [${project.id}] không có nội dung thô!`);

            // 2. LƯỢT 1: Gửi Skill Kịch Bản + Bản Thô
            updateStatusWidget(`[1/2] Đang viết kịch bản [${project.id}]...`, "#8b5cf6");
            const prompt1 = `${scriptSkill}\n\n${rawContent}`;
            await typeIntoChat(prompt1);
            await sleep(800);
            await clickSend();

            // Chờ Claude viết xong kịch bản
            const done1 = await waitForClaudeDone(300);
            if (!done1) throw new Error("Claude xử lý kịch bản quá thời gian!");

            // 3. LƯỢT 2: Gửi Skill Gợi Ý Tiêu Đề & Thumbnail
            updateStatusWidget(`[2/2] Đang xin Tiêu đề & Thumb [${project.id}]...`, "#3b82f6");
            await sleep(2000);
            const prompt2 = `${titleThumbSkill}\n\nHãy gợi ý 3 tiêu đề hấp dẫn và 1 đoạn prompt mô tả ảnh thumbnail (tiếng Anh và tiếng Việt) cho kịch bản vừa tạo ở trên.`;
            await typeIntoChat(prompt2);
            await sleep(800);
            await clickSend();

            // Chờ Claude phản hồi lượt 2
            const done2 = await waitForClaudeDone(150);
            if (!done2) throw new Error("Claude gợi ý tiêu đề/thumb quá thời gian!");

            // 4. Bóc tách kết quả
            const responses = getClaudeResponses();
            const fullScript = responses[responses.length - 2] || responses[0] || "";
            const titleThumbText = responses[responses.length - 1] || "";

            // Trích xuất tiêu đề
            let title = project.title || "";
            const titleLines = titleThumbText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
            for (const line of titleLines) {
                if (line.match(/(tiêu đề|title|1\.|-)/i) && line.length > 8 && line.length < 120) {
                    title = line.replace(/^(tiêu đề|title|1\.|2\.|3\.|-|\*|\"|\:)+/i, '').replace(/[\"\*]/g, '').trim();
                    if (title.length > 8) break;
                }
            }
            if (!title || title.startsWith("Bản thô:")) {
                title = titleLines[0] ? titleLines[0].substring(0, 70) : `Kịch bản ${project.id}`;
            }

            // Gửi dữ liệu về xưởng
            updateStatusWidget(`💾 Đang lưu [${project.id}] về Xưởng...`, "#6366f1");
            await apiFetch(`/api/projects/${project.id}/ai-complete`, {
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

    // Tự động kiểm tra URL xem có gắn cờ auto_kb=KBxxx không
    async function checkAutoRunFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const autoKbId = urlParams.get('auto_kb');

        if (!autoKbId) return;

        // Xóa tham số trên URL để tránh lặp khi refresh
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);

        updateStatusWidget(`🚀 Tìm thấy kịch bản [${autoKbId}]. Đang tải dữ liệu...`, "#f59e0b");

        try {
            // Lấy thông tin kịch bản từ server
            const projData = await apiFetch(`/api/projects/${autoKbId}`);
            const project = projData.project || projData;

            if (!project || (!project.raw_content && !project.content)) {
                updateStatusWidget(`⚠️ Không tìm thấy nội dung của [${autoKbId}]`, "#ef4444");
                return;
            }

            // Chờ khung chat sẵn sàng
            updateStatusWidget(`⏳ Chuẩn bị chạy 2 Skill cho [${autoKbId}] trong 2s...`, "#8b5cf6");
            await sleep(2500);

            // Bắt đầu chạy tự động
            runTwoSkillPipeline(project);

        } catch (err) {
            console.error("Lỗi tự động chạy từ URL:", err);
            updateStatusWidget(`❌ Lỗi kết nối Xưởng: ${err.message}`, "#ef4444");
        }
    }

    // Khởi tạo
    setTimeout(() => {
        createFloatingWidget();
        refreshPendingList();
        checkAutoRunFromUrl();
        setInterval(refreshPendingList, 15000);
    }, 1500);

})();
