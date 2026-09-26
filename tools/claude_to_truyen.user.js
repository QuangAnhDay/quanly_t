// ==UserScript==
// @name         Claude to Truyen Auto Producer (2-Skill Automation)
// @namespace    http://tampermonkey.net/
// @version      2.2
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

    const sleep = (ms) => new Promise(res => setTimeout(res, ms));

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

    function getChatInput() {
        return document.querySelector('div.ProseMirror[contenteditable="true"]') ||
               document.querySelector('div[contenteditable="true"]') ||
               document.querySelector('fieldset div[contenteditable="true"]');
    }

    function getSendButton() {
        return document.querySelector('button[aria-label*="Send"]') ||
               document.querySelector('button[aria-label*="Gửi"]') ||
               document.querySelector('button[type="submit"]') ||
               document.querySelector('button.bg-text-000') ||
               document.querySelector('fieldset button:last-child');
    }

    function isClaudeStreaming() {
        const stopBtn = document.querySelector('button[aria-label*="Stop"], button[aria-label*="Dừng"]');
        const streamingEl = document.querySelector('[data-is-streaming="true"]');
        return !!(stopBtn || streamingEl);
    }

    async function waitForElement(getterFn, maxWaitSeconds = 15) {
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            const el = getterFn();
            if (el) return el;
            await sleep(500);
        }
        return null;
    }

    async function waitForClaudeStart(expectedMinResponses = 1, maxWaitSeconds = 45, statusPrefix = "") {
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            const currentResponses = getClaudeResponses();
            const streaming = isClaudeStreaming();
            if (streaming || currentResponses.length >= expectedMinResponses) {
                return true;
            }
            const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
            if (statusPrefix) {
                updateStatusWidget(`${statusPrefix} (Đang chờ Claude bắt đầu ${elapsedSec}s)...`, "#8b5cf6");
            }
            await sleep(1000);
        }
        return false;
    }

    function handleContinueIfPresent() {
        const buttons = Array.from(document.querySelectorAll('button'));
        const continueBtn = buttons.find(b => {
            const text = (b.innerText || b.textContent || '').toLowerCase().trim();
            return (text.includes('continue') || text.includes('tiếp tục')) && !b.closest('fieldset');
        });
        if (continueBtn && !continueBtn.disabled) {
            console.log("--> 🔄 Thấy nút 'Tiếp tục / Continue', tự động bấm để Claude viết tiếp kịch bản dài...");
            continueBtn.click();
            return true;
        }
        return false;
    }

    async function waitForClaudeDone(expectedMinResponses = 1, maxWaitSeconds = 1800, statusPrefix = "") {
        // 1. Chờ Claude BẮT ĐẦU xử lý (tối đa 45s cho suy nghĩ ngầm / extended thinking)
        await waitForClaudeStart(expectedMinResponses, 45, statusPrefix);
        await sleep(2500);

        // 2. Chờ Claude HOÀN TẤT viết
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitSeconds * 1000) {
            if (!isClaudeStreaming()) {
                await sleep(3000);
                if (!isClaudeStreaming()) {
                    // Kiểm tra xem Claude có bị ngắt giữa chừng do hết token không (nút Continue/Tiếp tục)
                    const continued = handleContinueIfPresent();
                    if (continued) {
                        await sleep(3000);
                        continue;
                    }
                    return true;
                }
            }

            const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
            if (elapsedSec > 5 && statusPrefix) {
                const mins = Math.floor(elapsedSec / 60);
                const secs = elapsedSec % 60;
                const timeStr = mins > 0 ? `${mins}ph ${secs}s` : `${secs}s`;
                updateStatusWidget(`${statusPrefix} (Đang xử lý ${timeStr})...`, "#8b5cf6");
            }

            await sleep(1000);
        }
        return false;
    }

    // Nhập text bằng cơ chế Paste giả lập (tương thích 100% ProseMirror của Claude)
    async function typeIntoChat(text) {
        const input = await waitForElement(getChatInput, 15);
        if (!input) throw new Error("Không tìm thấy khung chat Claude!");

        input.focus();
        await sleep(300);

        // Tạo sự kiện Paste giả lập
        const dt = new DataTransfer();
        dt.setData('text/plain', text);
        const pasteEvent = new ClipboardEvent('paste', {
            bubbles: true,
            cancelable: true,
            clipboardData: dt
        });
        input.dispatchEvent(pasteEvent);

        // Fallback nếu Paste bị chặn
        if (!input.innerText || input.innerText.trim().length === 0) {
            document.execCommand('insertText', false, text);
        }

        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(800);
    }

    async function clickSend() {
        await sleep(400);
        const btn = getSendButton();
        if (btn && !btn.disabled) {
            btn.click();
            return true;
        }
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

    function getClaudeResponses() {
        // Prioritize specific Claude assistant message nodes
        let nodes = Array.from(document.querySelectorAll('.font-claude-message, [data-is-streaming], div.grid-cols-1, div.prose'));
        if (nodes.length === 0) {
            nodes = Array.from(document.querySelectorAll('.whitespace-pre-wrap'));
        }

        const texts = [];
        for (const node of nodes) {
            // Exclude user inputs / ProseMirror editor elements / user messages
            if (node.closest('[contenteditable="true"]') || node.closest('fieldset') || node.closest('[data-testid="user-message"]')) {
                continue;
            }

            const text = node.innerText ? node.innerText.trim() : '';
            if (!text) continue;

            // Exclude user skill commands if captured accidentally
            if (text.startsWith('/')) {
                continue;
            }

            if (!texts.includes(text)) {
                // Avoid redundant nested duplicate text blocks
                const isSubstring = texts.some(existing => existing.includes(text));
                if (!isSubstring) {
                    const existingIndex = texts.findIndex(existing => text.includes(existing));
                    if (existingIndex !== -1) {
                        texts[existingIndex] = text;
                    } else {
                        texts.push(text);
                    }
                }
            }
        }
        return texts;
    }

    function getLatestClaudeResponse() {
        const responses = getClaudeResponses();
        return responses.length > 0 ? responses[responses.length - 1] : "";
    }

    function getWordCount(str) {
        if (!str) return 0;
        return str.trim().split(/\s+/).filter(Boolean).length;
    }

    async function runTwoSkillPipeline(project) {
        if (isAutoRunning) return;
        isAutoRunning = true;
        const p1Status = `[1/2] Đang viết kịch bản [${project.id}]`;
        updateStatusWidget(`⏳ ${p1Status}...`, "#eab308");

        try {
            const skillConfig = await apiFetch('/api/claude-skill-config').catch(() => ({
                script_skill_command: '/tao-kich-ban',
                title_thumb_skill_command: '/tieu-de-thumb'
            }));

            const scriptSkill = (skillConfig.script_skill_command || '/tao-kich-ban').trim();
            const titleThumbSkill = (skillConfig.title_thumb_skill_command || '/tieu-de-thumb').trim();

            const rawContent = project.raw_content || project.content || "";
            if (!rawContent) throw new Error(`Kịch bản [${project.id}] không có nội dung thô!`);

            const initialCount = getClaudeResponses().length;

            // 1. LƯỢT 1: Tạo kịch bản chính (Cho phép tối đa 30 phút = 1800s cho Claude Extended Thinking & Kịch bản dài)
            updateStatusWidget(`[1/2] Đang viết kịch bản [${project.id}]...`, "#8b5cf6");
            const prompt1 = `${scriptSkill}\n\n${rawContent}`;
            await typeIntoChat(prompt1);
            await sleep(800);
            await clickSend();

            const done1 = await waitForClaudeDone(initialCount + 1, 1800, p1Status);
            if (!done1) throw new Error("Claude xử lý kịch bản quá thời gian (hơn 30 phút)!");

            // Bóc tách tất cả các đoạn phản hồi của Lượt 1 (kể cả khi bấm Tiếp Tục nhiều lần)
            const responsesAfterP1 = getClaudeResponses();
            const p1Responses = responsesAfterP1.slice(initialCount);
            let fullScript = p1Responses.join("\n\n").trim();
            if (!fullScript) {
                fullScript = getLatestClaudeResponse();
            }

            const wordCount1 = getWordCount(fullScript);
            const charCount1 = fullScript ? fullScript.length : 0;
            console.log(`--> [Lượt 1] Kịch bản chính (${wordCount1} từ, ${charCount1} ký tự):`, fullScript.substring(0, 100) + "...");

            // Bắt buộc kiểm tra độ dài tối thiểu (đảm bảo không bị lấy rỗng hoặc câu trả lời bị cụt)
            if (charCount1 < 300 || wordCount1 < 50) {
                throw new Error(`Kịch bản Lượt 1 quá ngắn hoặc rỗng (${wordCount1} từ, ${charCount1} ký tự)! Vui lòng kiểm tra lại Claude.`);
            }

            // 💾 LƯU NGAY LƯỢT 1 VỀ HỆ THỐNG (Bảo vệ dữ liệu kịch bản trước khi chạy Lượt 2)
            updateStatusWidget(`💾 Đã hoàn thành Kịch Bản (${wordCount1} từ). Đang lưu Lượt 1...`, "#6366f1");
            await apiFetch(`/api/projects/${project.id}/ai-complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: project.title || `Kịch bản ${project.id}`,
                    content: fullScript,
                    thumb_prompt: "",
                    notes: `Đã lưu Lượt 1 Kịch Bản (${wordCount1} từ, ${charCount1} ký tự)`
                })
            });

            // 2. LƯỢT 2: Xin Tiêu đề & Thumbnail (Chỉ gửi duy nhất lệnh skill)
            const countBeforeP2 = getClaudeResponses().length;
            const p2Status = `[2/2] Đang xin Tiêu đề & Thumb [${project.id}]`;
            updateStatusWidget(`⏳ ${p2Status}...`, "#3b82f6");
            await sleep(3000);

            const prompt2 = titleThumbSkill;
            await typeIntoChat(prompt2);
            await sleep(800);
            await clickSend();

            const done2 = await waitForClaudeDone(countBeforeP2 + 1, 600, p2Status);
            if (!done2) throw new Error("Claude gợi ý tiêu đề/thumb quá thời gian (hơn 10 phút)!");

            // Bóc tách câu trả lời Lượt 2
            const responsesAfterP2 = getClaudeResponses();
            const p2Responses = responsesAfterP2.slice(countBeforeP2);
            let titleThumbText = p2Responses.join("\n\n").trim();
            if (!titleThumbText) {
                titleThumbText = getLatestClaudeResponse();
            }
            console.log("--> [Lượt 2] Tiêu đề & Thumb:", titleThumbText.substring(0, 100) + "...");

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

            // 💾 LƯU CẬP NHẬT TRỌN BỘ 2-SKILL VỀ HỆ THỐNG
            updateStatusWidget(`💾 Đang cập nhật trọn bộ [${project.id}] về Xưởng...`, "#6366f1");
            await apiFetch(`/api/projects/${project.id}/ai-complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    content: fullScript,
                    thumb_prompt: titleThumbText,
                    notes: `Claude AI 2-Skill hoàn tất trọn bộ (${wordCount1} từ)`
                })
            });

            updateStatusWidget(`✅ Đã xong trọn bộ [${project.id}] (${wordCount1} từ)!`, "#22c55e");
            setTimeout(refreshPendingList, 3000);

        } catch (err) {
            console.error("Lỗi 2-Skill Pipeline:", err);
            updateStatusWidget(`❌ Lỗi: ${err.message}`, "#ef4444");
        } finally {
            isAutoRunning = false;
        }
    }

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

    async function checkAutoRunFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const autoKbId = urlParams.get('auto_kb');
        if (!autoKbId) return;

        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);

        updateStatusWidget(`🚀 Tìm thấy kịch bản [${autoKbId}]. Đang tải dữ liệu...`, "#f59e0b");

        try {
            const projData = await apiFetch(`/api/projects/${autoKbId}`);
            const project = projData.project || projData;

            if (!project || (!project.raw_content && !project.content)) {
                updateStatusWidget(`⚠️ Không tìm thấy nội dung của [${autoKbId}]`, "#ef4444");
                return;
            }

            updateStatusWidget(`⏳ Chuẩn bị chạy 2 Skill cho [${autoKbId}] trong 2s...`, "#8b5cf6");
            await sleep(2500);
            runTwoSkillPipeline(project);

        } catch (err) {
            console.error("Lỗi tự động chạy từ URL:", err);
            updateStatusWidget(`❌ Lỗi kết nối Xưởng: ${err.message}`, "#ef4444");
        }
    }

    setTimeout(() => {
        createFloatingWidget();
        refreshPendingList();
        checkAutoRunFromUrl();
        setInterval(refreshPendingList, 15000);
    }, 1500);

})();
