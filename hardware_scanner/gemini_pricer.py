"""
O2O Laptop Inspection - Gemini AI Pricer
Gọi Gemini API để phân tích cấu hình + kết quả kiểm định → đề xuất giá.
"""

import json
import ssl
import urllib.request
import urllib.error

from config import GEMINI_API_KEY, GEMINI_MODEL


def _make_endpoint():
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )


def _ssl_context():
    """SSL context dùng certifi CA bundle (fix lỗi certificate trên macOS/PyInstaller)."""
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    return ctx


def _build_prompt(hw: dict, answers: dict, checklist: list, grade: str, score: int) -> str:
    s    = hw.get("system", {})
    cpu  = hw.get("cpu", {})
    ram  = hw.get("ram", {})
    batt = hw.get("battery", {})
    disks = hw.get("storage", [])
    gpus  = hw.get("gpu", [])

    # Tóm tắt cấu hình
    disk_str = ", ".join(
        f"{d['name']} {d['size_gb']}GB ({d['interface']})" for d in disks
    ) or "Không rõ"

    gpu_str = ", ".join(
        f"{g.get('name','?')}" +
        (f" {g['vram_gb']}GB VRAM" if g.get("vram_gb") else "") +
        f" [{g.get('type','')}]"
        for g in gpus
    ) or "Không rõ"

    ram_slots = ram.get("slots", [])
    ram_detail = ", ".join(
        f"{sl['capacity_gb']}GB {sl['type']} {sl['speed_mhz']}MHz"
        for sl in ram_slots
    ) or f"{ram.get('total_gb','?')}GB"

    batt_str = "Không có pin"
    if batt.get("present"):
        h = batt.get("health_percent")
        c = batt.get("cycle_count")
        batt_str = f"Sức khỏe pin: {h}%" if h else "Có pin"
        if c:
            batt_str += f", {c} lần sạc"

    # Tóm tắt checklist
    cl_map = {item["id"]: item for item in checklist}
    cl_lines = []
    for qid, idx in answers.items():
        item = cl_map.get(qid)
        if item and idx >= 0:
            opt = item["options"][idx]
            flag = " 🚩" if opt.get("red_flag") else f" (+{opt['score']}đ)"
            cl_lines.append(f"  - {item['category']}: {opt['label']}{flag}")
    cl_summary = "\n".join(cl_lines) or "  (Chưa có kết quả kiểm định)"

    prompt = f"""Bạn là chuyên gia định giá laptop cũ tại thị trường Việt Nam (năm 2025).
Phân tích thông tin sau và trả về JSON CHÍNH XÁC theo format yêu cầu.

=== CẤU HÌNH MÁY ===
Hãng / Model  : {s.get('manufacturer','')} {s.get('model','')}
Serial Number : {s.get('serial_number','')}
CPU           : {cpu.get('name','')} ({cpu.get('physical_cores','?')} lõi, {cpu.get('max_freq_ghz','?')} GHz)
RAM           : {ram.get('total_gb','?')} GB ({ram_detail})
Ổ cứng        : {disk_str}
Card đồ họa   : {gpu_str}
Pin           : {batt_str}

=== KẾT QUẢ KIỂM ĐỊNH NGOẠI QUAN ===
Xếp hạng : {grade}  |  Tổng điểm phạt: {score}
{cl_summary}

=== YÊU CẦU OUTPUT ===
Trả về JSON hợp lệ (không có text thừa, không có markdown), đơn vị giá là VNĐ nguyên (số nguyên):

{{
  "buy_min": <giá thu mua thấp nhất, số nguyên VNĐ>,
  "buy_max": <giá thu mua cao nhất, số nguyên VNĐ>,
  "summary": "<đánh giá tổng quan 1-2 câu>",
  "strengths": ["<điểm mạnh 1>", "<điểm mạnh 2>"],
  "weaknesses": ["<điểm yếu 1>", "<điểm yếu 2>"],
  "reasoning": "<lý do định giá ngắn gọn>"
}}"""

    return prompt


def parse_result(raw: str) -> dict:
    """Parse JSON từ response Gemini. Fallback về dict rỗng nếu lỗi."""
    text = raw.strip()
    # Bỏ markdown code block nếu có
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Thử tìm JSON object trong text
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
        return {"_raw": raw}  # fallback giữ text gốc


def get_price_estimate(hw: dict, answers: dict, checklist: list,
                       grade: str, score: int) -> str:
    """
    Gọi Gemini API và trả về string kết quả.
    Raise Exception nếu lỗi.
    """
    prompt = _build_prompt(hw, answers, checklist, grade, score)

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        _make_endpoint(),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini không trả về kết quả")
            text = candidates[0]["content"]["parts"][0]["text"]
            return text.strip()

    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini API lỗi {e.code}: {body_err[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Không kết nối được Gemini: {e.reason}")
