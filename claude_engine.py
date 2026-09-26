import os
import sys
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
    Lưu nhật ký gốc vào outputs/{project_id}/claude_raw_log.txt
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

    # 1. Nếu có Anthropic API Key -> Chạy bằng Anthropic API SDK chính thức
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

    # 2. Fallback: Dùng Playwright Headless Browser (Chạy hoàn toàn ẩn ngầm 100%, 0 mở cửa sổ GUI)
    try:
        from playwright.async_api import async_playwright
        if on_progress:
            on_progress("Đang khởi động tiến trình Claude Headless ngầm...", 15, 0)

        async with async_playwright() as p:
            # Launch invisible Chrome
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            write_raw_log("MODE", "Playwright Headless Ngầm")
            
            # Navigate to claude.ai
            await page.goto("https://claude.ai/new", timeout=60000)
            await page.wait_for_timeout(3000)

            # Check if chat box present
            input_selector = 'div.ProseMirror[contenteditable="true"], div[contenteditable="true"]'
            await page.wait_for_selector(input_selector, timeout=15000)

            prompt1 = f"{script_skill}\n\n{raw_content}"
            await page.fill(input_selector, prompt1)
            await page.keyboard.press("Enter")

            if on_progress:
                on_progress("Đang gửi Prompt 1 và chờ Claude ngầm trả lời...", 30, 0)

            # Wait for generation done
            await page.wait_for_selector('[data-is-streaming="false"]', timeout=300000)
            await page.wait_for_timeout(3000)

            # Extract response 1
            messages = await page.eval_on_selector_all(
                '.font-claude-message, [data-is-streaming="false"]',
                'nodes => nodes.map(n => n.innerText)'
            )
            script_text = messages[-1] if messages else ""
            words1 = count_words(script_text)
            write_raw_log("LƯỢT 1: KỊCH BẢN CHÍNH (Headless)", script_text)

            if on_progress:
                on_progress(f"Đã hoàn thành Kịch Bản ngầm ({words1} từ). Đang gửi Lượt 2...", 65, words1)

            # Lượt 2
            await page.fill(input_selector, title_thumb_skill)
            await page.keyboard.press("Enter")
            await page.wait_for_selector('[data-is-streaming="false"]', timeout=180000)
            await page.wait_for_timeout(3000)

            messages2 = await page.eval_on_selector_all(
                '.font-claude-message, [data-is-streaming="false"]',
                'nodes => nodes.map(n => n.innerText)'
            )
            title_thumb_text = messages2[-1] if messages2 else ""
            write_raw_log("LƯỢT 2: TIÊU ĐỀ & THUMB (Headless)", title_thumb_text)

            await browser.close()

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
                "mode": "headless_browser"
            }
    except Exception as err:
        logger.error(f"Lỗi Claude Engine Headless: {err}")
        write_raw_log("LỖI ENGINE HEADLESS", str(err))
        raise RuntimeError(f"Claude Engine thất bại: {err}")
