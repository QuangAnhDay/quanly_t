import os
import json
import uuid
import re
import csv
import io
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

def extract_row_data(line: str) -> Optional[Dict[str, Any]]:
    """
    Tự động nhận diện dữ liệu copy-paste từ Excel, Google Sheets, CSV, hoặc text:
    - Nhận diện delimiter: tab (\t), pipe (|), comma (,), semicolon (;)
    - Tự động tìm ô nào chứa Link URL (bắt đầu bằng http, https, hoặc có chứa shopee)
    - Tự động lấy các ô còn lại làm tên/nội dung bình luận (bất kể thứ tự cột)
    - Tự động bỏ qua các dòng tiêu đề (Header rows: STT, Tên SP, Link Shopee, URL...)
    """
    line = line.strip()
    if not line:
        return None

    # Tách các cột theo delimiter ưu tiên: \t (Excel/Sheets) > | > ; > ,
    if '\t' in line:
        raw_parts = line.split('\t')
    elif '|' in line:
        raw_parts = line.split('|')
    elif ';' in line:
        raw_parts = line.split(';')
    elif ',' in line:
        try:
            reader = csv.reader(io.StringIO(line))
            raw_parts = next(reader)
        except Exception:
            raw_parts = line.split(',')
    else:
        raw_parts = [line]

    parts = [p.strip().strip('"').strip("'") for p in raw_parts if p.strip()]
    if not parts:
        return None

    # Kiểm tra header row (ví dụ copy cả dòng tiêu đề của bảng tính)
    header_keywords = {"stt", "no", "tên sản phẩm", "ten san pham", "sản phẩm", "san pham", "tên sp", "ten sp", "link", "url", "link shopee", "comment", "bình luận", "ghi chú", "note"}
    if len(parts) >= 2 and all(p.lower() in header_keywords for p in parts):
        return {"is_header": True}

    # Tìm ô chứa URL
    url_index = -1
    for i, p in enumerate(parts):
        lower = p.lower()
        if lower.startswith("http://") or lower.startswith("https://") or "shopee.vn" in lower or "s.shopee" in lower:
            url_index = i
            break

    if url_index == -1:
        url_match = re.search(r'https?://[^\s]+', line)
        if url_match:
            link = url_match.group(0).strip('.,;)"\'')
            comment = line.replace(link, '').strip().strip('|').strip('\t').strip(',').strip(';')
            return {"comment": comment.strip() or "Sản phẩm xuất hiện trong video nha các bác", "link": link}
        return {"comment": " ".join(parts), "link": "", "error": "Không tìm thấy link URL hợp lệ"}

    link = parts[url_index]
    # Lấy các ô còn lại làm comment, loại bỏ ô số thứ tự (ví dụ: "1", "2", "3")
    other_parts = [p for i, p in enumerate(parts) if i != url_index and not re.match(r'^\d+$', p)]
    comment = " - ".join(other_parts).strip()
    if not comment:
        comment = "Dụng cụ / sản phẩm xuất hiện trong video nha các bác"

    return {"comment": comment, "link": link}

def preview_parsed_links(theme: str, raw_text: str) -> Dict[str, Any]:
    """
    Phân tích văn bản dán từ Excel / Google Sheets và trả về bản xem trước (Live Preview):
    - Đánh dấu trạng thái từng dòng: hợp lệ, trùng lặp, lỗi
    - Chuẩn bị dữ liệu hiển thị bảng tương tác trước khi bấm lưu
    """
    data = load_affiliate_data()
    theme_links = data.get(theme, [])
    existing_urls = {normalize_url(item.get("link", "")) for item in theme_links}

    lines = raw_text.strip().split("\n")
    rows = []
    seen_in_batch = set()

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        res = extract_row_data(line)
        if not res or res.get("is_header"):
            continue

        comment = res.get("comment", "")
        link = res.get("link", "")
        error = res.get("error", "")

        if error or not link:
            rows.append({
                "row_idx": idx + 1,
                "comment": comment,
                "link": link,
                "status": "invalid",
                "reason": error or "Thiếu link Shopee hợp lệ",
                "can_add": False
            })
            continue

        norm = normalize_url(link)
        if norm in existing_urls:
            rows.append({
                "row_idx": idx + 1,
                "comment": comment,
                "link": link,
                "status": "duplicate",
                "reason": "Link này đã có trong kho",
                "can_add": False
            })
        elif norm in seen_in_batch:
            rows.append({
                "row_idx": idx + 1,
                "comment": comment,
                "link": link,
                "status": "duplicate",
                "reason": "Trùng lặp ngay trong danh sách dán",
                "can_add": False
            })
        else:
            seen_in_batch.add(norm)
            rows.append({
                "row_idx": idx + 1,
                "comment": comment,
                "link": link,
                "status": "valid",
                "reason": "Hợp lệ",
                "can_add": True
            })

    valid_count = sum(1 for r in rows if r["status"] == "valid")
    dup_count = sum(1 for r in rows if r["status"] == "duplicate")
    inv_count = sum(1 for r in rows if r["status"] == "invalid")

    return {
        "success": True,
        "rows": rows,
        "stats": {
            "total_rows": len(rows),
            "valid_count": valid_count,
            "duplicate_count": dup_count,
            "invalid_count": inv_count
        }
    }

def batch_add_links(theme: str, raw_text: Optional[str] = None, items: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Nạp hàng loạt vào kho:
    - Chấp nhận hoặc raw_text (tự bóc tách từ Excel/Sheets) hoặc items (danh sách đã lọc từ UI)
    - Tự động lọc trùng thông minh
    """
    data = load_affiliate_data()
    theme_links = data.get(theme, [])
    existing_urls = {normalize_url(item.get("link", "")) for item in theme_links}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    added = []
    duplicates = []
    invalid = []

    # Nếu gửi danh sách items trực tiếp từ Live Preview UI
    if items is not None:
        for item in items:
            comment = (item.get("comment") or "").strip()
            link = (item.get("link") or "").strip()
            if not link or not (link.startswith("http://") or link.startswith("https://")):
                invalid.append({"comment": comment, "link": link, "reason": "Link URL không hợp lệ"})
                continue

            norm = normalize_url(link)
            if norm in existing_urls:
                duplicates.append({"comment": comment, "link": link})
                continue

            new_item = {
                "id": f"aff_{uuid.uuid4().hex[:8]}",
                "comment": comment or "Dụng cụ xuất hiện trong video cho bạn nào cần nhé",
                "link": link,
                "used_count": 0,
                "created_at": now
            }
            theme_links.append(new_item)
            existing_urls.add(norm)
            added.append(new_item)
    elif raw_text:
        preview = preview_parsed_links(theme, raw_text)
        for row in preview.get("rows", []):
            if row.get("status") == "valid":
                new_item = {
                    "id": f"aff_{uuid.uuid4().hex[:8]}",
                    "comment": row["comment"],
                    "link": row["link"],
                    "used_count": 0,
                    "created_at": now
                }
                theme_links.append(new_item)
                existing_urls.add(normalize_url(row["link"]))
                added.append(new_item)
            elif row.get("status") == "duplicate":
                duplicates.append({"comment": row["comment"], "link": row["link"]})
            else:
                invalid.append({"comment": row["comment"], "link": row["link"], "reason": row.get("reason", "")})

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
