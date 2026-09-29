import os
import json
import uuid
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
import task_logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AFFILIATE_FILE = os.path.join(DATA_DIR, "affiliate_links.json")

DEFAULT_THEMES = ["nau_an", "handmade"]

def load_affiliate_data() -> Dict[str, List[Dict[str, Any]]]:
    """Đọc kho link affiliate từ file JSON"""
    if os.path.exists(AFFILIATE_FILE):
        try:
            with open(AFFILIATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for t in DEFAULT_THEMES:
                    if t not in data:
                        data[t] = []
                return data
        except Exception as e:
            print(f"[AffiliateManager] Lỗi đọc affiliate_links.json: {e}")
    
    # Dữ liệu mẫu ban đầu
    initial = {
        "nau_an": [],
        "handmade": []
    }
    save_affiliate_data(initial)
    return initial

def save_affiliate_data(data: Dict[str, List[Dict[str, Any]]]):
    """Lưu kho link affiliate vào file JSON"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(AFFILIATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AffiliateManager] Lỗi lưu affiliate_links.json: {e}")

def normalize_url(url: str) -> str:
    """Chuẩn hóa URL để kiểm tra trùng lặp chuẩn xác (bỏ query parameter, khoảng trắng, slash cuối)"""
    if not url:
        return ""
    u = url.strip()
    # Loại bỏ giao thức để so sánh domain + path
    u = re.sub(r'^https?://', '', u)
    # Loại bỏ dấu / ở cuối và query string (?...)
    u = u.split('?')[0].rstrip('/')
    return u.lower()

def get_links_by_theme(theme: str = "nau_an") -> List[Dict[str, Any]]:
    """Lấy danh sách link theo chủ đề"""
    data = load_affiliate_data()
    return data.get(theme, [])

def batch_add_links(theme: str, raw_text: str) -> Dict[str, Any]:
    """
    Dán hàng loạt theo định dạng: Mỗi dòng 1 sản phẩm:
    'Nội dung comment | Link Shopee'
    Tự động lọc trùng: Nếu link đã tồn tại trong kho thì bỏ qua.
    """
    data = load_affiliate_data()
    theme_links = data.get(theme, [])

    # Tập hợp các link đã tồn tại để chống trùng
    existing_urls = {normalize_url(item.get("link", "")) for item in theme_links}

    lines = raw_text.strip().split("\n")
    added = []
    duplicates = []
    invalid = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        parts = [p.strip() for p in re.split(r'[|\t]', line) if p.strip()]
        
        comment = ""
        link = ""

        if len(parts) >= 2:
            comment = parts[0]
            link = parts[1]
        elif len(parts) == 1:
            # Nếu chỉ dán 1 URL
            candidate = parts[0]
            if candidate.startswith("http") or "shopee" in candidate.lower():
                link = candidate
                comment = "Sản phẩm đồ bếp / dụng cụ xuất hiện trong clip"
            else:
                comment = candidate
                link = ""

        if not link or not (link.startswith("http://") or link.startswith("https://")):
            invalid.append({"line": line, "reason": "Không tìm thấy link URL hợp lệ"})
            continue

        norm = normalize_url(link)
        if norm in existing_urls:
            duplicates.append({"comment": comment, "link": link})
            continue

        item = {
            "id": f"aff_{uuid.uuid4().hex[:8]}",
            "comment": comment or "Dụng cụ xuất hiện trong video cho bạn nào cần nhé",
            "link": link,
            "used_count": 0,
            "created_at": now
        }
        theme_links.append(item)
        existing_urls.add(norm)
        added.append(item)

    data[theme] = theme_links
    save_affiliate_data(data)

    task_logger.add_log(
        "system",
        f"🛒 [Kho Shopee] Nạp hàng loạt vào kho [{theme}]: Thêm {len(added)} link mới, loại bỏ {len(duplicates)} link trùng.",
        "success"
    )

    return {
        "success": True,
        "added_count": len(added),
        "duplicate_count": len(duplicates),
        "invalid_count": len(invalid),
        "total_count": len(theme_links),
        "added": added,
        "duplicates": duplicates
    }

def update_or_add_single_link(theme: str, comment: str, link: str, link_id: Optional[str] = None) -> Dict[str, Any]:
    """Thêm mới hoặc sửa 1 dòng trong kho"""
    data = load_affiliate_data()
    theme_links = data.get(theme, [])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    norm = normalize_url(link)

    if link_id:
        # Cập nhật dòng cũ
        for item in theme_links:
            if item.get("id") == link_id:
                item["comment"] = comment.strip()
                item["link"] = link.strip()
                item["updated_at"] = now
                save_affiliate_data(data)
                return {"success": True, "item": item, "is_new": False}
        return {"success": False, "error": "Không tìm thấy ID"}

    # Thêm mới: kiểm tra trùng
    for item in theme_links:
        if normalize_url(item.get("link", "")) == norm:
            return {"success": False, "error": "Link sản phẩm này đã có trong kho!"}

    new_item = {
        "id": f"aff_{uuid.uuid4().hex[:8]}",
        "comment": comment.strip(),
        "link": link.strip(),
        "used_count": 0,
        "created_at": now
    }
    theme_links.append(new_item)
    data[theme] = theme_links
    save_affiliate_data(data)
    return {"success": True, "item": new_item, "is_new": True}

def delete_link(theme: str, link_id: str) -> bool:
    """Xóa 1 link khỏi kho"""
    data = load_affiliate_data()
    theme_links = data.get(theme, [])
    filtered = [item for item in theme_links if item.get("id") != link_id]
    if len(filtered) != len(theme_links):
        data[theme] = filtered
        save_affiliate_data(data)
        return True
    return False

def pick_affiliate_link(theme: str = "nau_an", project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Thuật toán Xoay Tua bốc link theo tag:
    - Bốc link có số lần dùng (used_count) ít nhất trong kho của theme.
    - Tăng số lần dùng lên 1.
    - Trả về comment + link để cắm vào bài đăng.
    """
    data = load_affiliate_data()
    theme_links = data.get(theme, [])

    # Nếu kho của theme này trống, thử fallback sang kho nau_an hoặc bất kỳ kho nào có link
    if not theme_links:
        for t, links in data.items():
            if links:
                theme_links = links
                break

    if not theme_links:
        return None

    # Tìm link có used_count nhỏ nhất
    min_count = min(item.get("used_count", 0) for item in theme_links)
    candidates = [item for item in theme_links if item.get("used_count", 0) == min_count]

    import random
    chosen = random.choice(candidates)
    chosen["used_count"] = chosen.get("used_count", 0) + 1
    chosen["last_used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_affiliate_data(data)

    msg = f"🛒 [Shopee Affiliate] Đã bốc link theo tag [{theme}]: {chosen['comment']} ({chosen['link']})"
    task_logger.add_log("pipeline", msg, "info", project_id)
    try:
        print(f"[AffiliateManager] {msg}")
    except Exception:
        pass

    return chosen
