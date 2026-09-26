import os
import sys
import re
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("claude_engine")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.strip().split())

async def run_claude_2skill_backend(
    project_id: str,
    raw_content: str,
    script_skill: str = "/tao-kich-ban",
    title_thumb_skill: str = "/tieu-de-thumb",
    on_progress: Optional[Callable[[str, int, int], None]] = None
) -> Dict[str, Any]:
    """
    Thực thi 2-Skill Claude ngầm bằng Python Engine.
    Hỗ trợ Anthropic Official API, Chrome Persistent Context (Profile đã đăng nhập), và SessionKey Cookie.
    Lưu nhật ký thô vào outputs/{project_id}/{project_id}_claude_raw_log.txt
    """
    cfg = get_config()
    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    
    pkg_dir = os.path.join(os.path.dirname(__file__), "outputs", project_id)
    os.makedirs(pkg_dir, exist_ok=True)
    raw_log_path = os.path.join(pkg_dir, f"{project_id}_claude_raw_log.txt")

    def write_raw_log(section_title: str, content: str):
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(raw_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== [{now_str}] {section_title} ===\n")
            f.write(content.strip() + "\n")

    # 1. Ưu tiên: Nếu có Anthropic API Key -> Chạy bằng Anthropic API chính thức
    if api_key:
        try:
            import httpx
            if on_progress:
                on_progress("Đang gọi Claude API ngầm...", 10, 0)

            prompt1 = f"{script_skill}\n\n{raw_content}"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload1 = {
                "model": cfg.get("claude_model") or "claude-3-5-sonnet-20241022",
                "max_tokens": 8192,
                "messages": [{"role": "user", "content": prompt1}]
            }

            async with httpx.AsyncClient(timeout=600.0) as client:
                res1 = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload1)
                data1 = res1.json()
                
                if "content" in data1 and len(data1["content"]) > 0:
                    script_text = data1["content"][0]["text"]
                else:
                    raise ValueError(f"Lỗi API Anthropic Lượt 1: {res1.text}")

                words1 = count_words(script_text)
                write_raw_log("LƯỢT 1: KỊCH BẢN CHÍNH (API)", script_text)

                if on_progress:
                    on_progress(f"Đã tạo xong Kịch Bản ({words1} từ). Đang xin Tiêu đề & Thumb...", 50, words1)

                # Lượt 2: Xin Tiêu đề & Thumb
                payload2 = {
                    "model": cfg.get("claude_model") or "claude-3-5-sonnet-20241022",
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "user", "content": prompt1},
                        {"role": "assistant", "content": script_text},
                        {"role": "user", "content": title_thumb_skill}
                    ]
                }
                res2 = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload2)
                data2 = res2.json()
                title_thumb_text = data2["content"][0]["text"] if "content" in data2 else ""
                write_raw_log("LƯỢT 2: TIÊU ĐỀ & THUMBNAIL (API)", title_thumb_text)

                title = ""
                for line in title_thumb_text.splitlines():
                    clean = line.strip()
                    if clean and len(clean) > 8 and len(clean) < 120:
                        title = clean.replace('"', '').replace('*', '').strip()
                        break
                if not title:
                    title = f"Kịch bản {project_id}"

                return {
                    "success": True,
                    "title": title,
                    "content": script_text,
                    "thumb_prompt": title_thumb_text,
                    "word_count": words1,
                    "raw_log_path": raw_log_path,
                    "mode": "official_api"
                }
        except Exception as e:
            logger.error(f"Lỗi Anthropic API: {e}")
            write_raw_log("LỖI API", str(e))

    # 2. Fallback: Dùng Playwright Headless Browser với Profile Chrome đã đăng nhập hoặc Cookie SessionKey
    try:
        from playwright.async_api import async_playwright
        if on_progress:
            on_progress("Đang khởi động trình duyệt Claude Headless ngầm...", 15, 0)

        async with async_playwright() as p:
            user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            profiles = cfg.get("chrome_profiles", ["Profile 7", "Profile 2", "Profile 4", "Profile 5", "Profile 1", "Default"])
            
            context = None
            page = None
            used_mode = "playwright_headless"

            # 2.1 Lần 1: Thử dùng Persistent Context với Profile Chrome đã đăng nhập sẵn trên máy
            if os.path.exists(user_data_dir):
                for prof in profiles:
                    prof_path = os.path.join(user_data_dir, prof)
                    if os.path.exists(prof_path):
                        try:
                            context = await p.chromium.launch_persistent_context(
                                user_data_dir=user_data_dir,
                                channel="chrome",
                                headless=True,
                                args=[f"--profile-directory={prof}"]
                            )
                            page = context.pages[0] if context.pages else await context.new_page()
                            used_mode = f"Playwright Persistent Chrome ({prof})"
                            break
                        except Exception as e_prof:
                            logger.warning(f"Không mở được profile {prof}: {e_prof}")
                            context = None

            # 2.2 Lần 2: Nếu chưa dùng được Persistent Context, dùng Chromium chuẩn
            if not context:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                used_mode = "Playwright Standard Headless"

            # 2.3 Nạp Cookie sessionKey nếu được cài đặt trong config.json hoặc biến môi trường
            session_key = cfg.get("claude_session_key") or os.environ.get("CLAUDE_SESSION_KEY")
            if session_key:
                if not session_key.startswith("sk-ant-sid01-") and "sk-ant-sid01-" in session_key:
                    m = re.search(r'sk-ant-sid01-[A-Za-z0-9_\-]+', session_key)
                    if m:
                        session_key = m.group(0)
                        
                await context.add_cookies([{
                    "name": "sessionKey",
                    "value": session_key,
                    "domain": ".claude.ai",
                    "path": "/"
                }])

            write_raw_log("MODE", used_mode)

            # Mở trang Claude.ai/new
            await page.goto("https://claude.ai/new", timeout=60000)
            await page.wait_for_timeout(3000)

            # Kiểm tra xem có bị bắt đăng nhập không
            if "login" in page.url:
                raise RuntimeError(
                    "Trình duyệt chưa đăng nhập Claude! Vui lòng mở Chrome đăng nhập Claude.ai trước, "
                    "hoặc dán sessionKey vào config.json ('claude_session_key': 'sk-ant-sid01-...')"
                )

            # Đợi khung chat xuất hiện
            input_selector = 'div.ProseMirror[contenteditable="true"], div[contenteditable="true"]'
            try:
                await page.wait_for_selector(input_selector, timeout=25000)
            except Exception:
                raise RuntimeError("Không tìm thấy khung chat Claude.ai (Có thể chưa đăng nhập tài khoản).")

            # 2.4 Gửi Prompt 1 (Tạo Kịch Bản)
            prompt1 = f"{script_skill}\n\n{raw_content}"
            await page.click(input_selector)
            await page.keyboard.insert_text(prompt1)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")

            if on_progress:
                on_progress("Đang gửi Prompt 1 và chờ Claude ngầm viết kịch bản...", 30, 0)

            # Chờ hoàn thành + tự động bấm Continue nếu kịch bản siêu dài
            max_wait_p1 = 1800 # 30 phút
            start_wait = time.time()
            while time.time() - start_wait < max_wait_p1:
                await page.wait_for_timeout(3000)
                is_streaming = await page.evaluate('''() => {
                    const stopBtn = document.querySelector('button[aria-label*="Stop"], button[aria-label*="Dừng"]');
                    const streamingEl = document.querySelector('[data-is-streaming="true"]');
                    return !!(stopBtn || streamingEl);
                }''')

                if not is_streaming:
                    # Kiểm tra nút Continue / Tiếp tục
                    btn_clicked = await page.evaluate('''() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const cont = buttons.find(b => {
                            const t = (b.innerText || '').toLowerCase();
                            return (t.includes('continue') || t.includes('tiếp tục')) && !b.closest('fieldset');
                        });
                        if (cont && !cont.disabled) {
                            cont.click();
                            return true;
                        }
                        return false;
                    }''')
                    if btn_clicked:
                        logger.info("Tự động bấm nút 'Tiếp tục' trên Playwright...")
                        await page.wait_for_timeout(3000)
                        continue
                    break

            # Lấy tất cả tin nhắn phản hồi của Claude
            messages1 = await page.eval_on_selector_all(
                '.font-claude-message, [data-is-streaming="false"]',
                '''nodes => nodes
                    .filter(n => !n.closest('[contenteditable="true"]') && !n.closest('fieldset') && !n.closest('[data-testid="user-message"]'))
                    .map(n => n.innerText)
                    .filter(t => t && !t.startsWith('/'))'''
            )

            script_text = "\n\n".join(messages1).strip() if messages1 else ""
            words1 = count_words(script_text)
            write_raw_log("LƯỢT 1: KỊCH BẢN CHÍNH (Headless)", script_text)

            if words1 < 50:
                raise ValueError(f"Kịch bản Lượt 1 ngầm trả về quá ngắn ({words1} từ)!")

            if on_progress:
                on_progress(f"Đã hoàn thành Kịch Bản ngầm ({words1} từ). Đang gửi Lượt 2...", 65, words1)

            # 2.5 Gửi Prompt 2 (Tiêu đề & Thumb)
            await page.click(input_selector)
            await page.keyboard.insert_text(title_thumb_skill)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")

            # Chờ Lượt 2 hoàn thành
            start_wait_p2 = time.time()
            while time.time() - start_wait_p2 < 300:
                await page.wait_for_timeout(3000)
                is_streaming2 = await page.evaluate('''() => {
                    const stopBtn = document.querySelector('button[aria-label*="Stop"], button[aria-label*="Dừng"]');
                    const streamingEl = document.querySelector('[data-is-streaming="true"]');
                    return !!(stopBtn || streamingEl);
                }''')
                if not is_streaming2:
                    break

            messages2 = await page.eval_on_selector_all(
                '.font-claude-message, [data-is-streaming="false"]',
                '''nodes => nodes
                    .filter(n => !n.closest('[contenteditable="true"]') && !n.closest('fieldset') && !n.closest('[data-testid="user-message"]'))
                    .map(n => n.innerText)
                    .filter(t => t && !t.startsWith('/'))'''
            )

            title_thumb_text = messages2[-1] if messages2 else ""
            write_raw_log("LƯỢT 2: TIÊU ĐỀ & THUMB (Headless)", title_thumb_text)

            try:
                if context:
                    await context.close()
            except Exception:
                pass

            title = ""
            for line in title_thumb_text.splitlines():
                clean = line.strip()
                if clean and len(clean) > 8 and len(clean) < 120:
                    title = clean.replace('"', '').replace('*', '').strip()
                    break
            if not title:
                title = f"Kịch bản {project_id}"

            return {
                "success": True,
                "title": title,
                "content": script_text,
                "thumb_prompt": title_thumb_text,
                "word_count": words1,
                "raw_log_path": raw_log_path,
                "mode": used_mode
            }
    except Exception as err:
        logger.error(f"Lỗi Claude Engine Headless: {err}")
        write_raw_log("LỖI ENGINE HEADLESS", str(err))
        raise RuntimeError(f"Claude Engine thất bại: {err}")
