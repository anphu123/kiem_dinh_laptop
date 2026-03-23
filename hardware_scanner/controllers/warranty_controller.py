"""
Controller: Tra cứu bảo hành trên thegioididong.com.

Dùng Playwright (headless Chromium) để:
  1. Mở trang /bao-hanh
  2. Fill keyword + click submit (page JS tự xử lý reCAPTCHA v3)
  3. Intercept XHR response từ /Warranty/ListWarantyInfo
  4. Parse JSON {code, data} → HTML fragment

Lưu ý: không POST thủ công — để trang tự submit tránh bot-detection.
"""
from __future__ import annotations

import threading
import webbrowser
from dataclasses import dataclass, field
from typing import Callable, Optional

from bs4 import BeautifulSoup


BASE = "https://www.thegioididong.com"
WARRANTY_PAGE = f"{BASE}/bao-hanh"


@dataclass
class WarrantyItem:
    product_name: str = ""
    serial: str = ""
    imei: str = ""
    purchase_date: str = ""
    warranty_end: str = ""
    warranty_status: str = ""   # "Còn bảo hành" | "Hết bảo hành" | ...
    store: str = ""
    status_color: str = "dim"   # "green" | "yellow" | "red" | "dim"
    raw_text: str = ""          # fallback khi không parse được fields


@dataclass
class WarrantyResult:
    success: bool = False
    keyword: str = ""
    items: list[WarrantyItem] = field(default_factory=list)
    raw_message: str = ""       # thông báo lỗi hoặc "không tìm thấy"
    error: str = ""
    need_browser: bool = False  # True → cần mở browser thủ công


class WarrantyController:
    def __init__(self):
        self._on_start:  Optional[Callable] = None
        self._on_result: Optional[Callable[[WarrantyResult], None]] = None
        self._running = False

    def set_callbacks(self, on_start: Optional[Callable] = None,
                      on_result: Optional[Callable[[WarrantyResult], None]] = None):
        self._on_start  = on_start
        self._on_result = on_result

    def reset(self):
        self._running = False

    def lookup(self, keyword: str, search_type: int = 2):
        """search_type: 1=SĐT, 2=IMEI/serial, 3=jobcard"""
        keyword = keyword.strip()
        if not keyword or self._running:
            return
        self._running = True
        if self._on_start:
            self._on_start()
        threading.Thread(
            target=self._run, args=(keyword, search_type), daemon=True
        ).start()

    def open_browser(self, keyword: str = ""):
        """Mở trang bảo hành TGDD trên browser mặc định."""
        webbrowser.open(WARRANTY_PAGE)

    # ── Private ───────────────────────────────────────────────────────────────

    def _run(self, keyword: str, search_type: int):
        result = WarrantyResult(keyword=keyword)
        try:
            self._lookup_playwright(keyword, search_type, result)
        except Exception as e:
            result.error = str(e)
            result.need_browser = True
        finally:
            self._running = False
            if self._on_result:
                self._on_result(result)

    def _lookup_playwright(self, keyword: str, search_type: int,
                           result: WarrantyResult):
        """
        Dùng Playwright headless:
        1. Mở /bao-hanh + attach page.on("response") listener
        2. Fill keyword + click KIỂM TRA (page JS tự xử lý reCAPTCHA v3)
        3. Poll với page.wait_for_timeout() → giữ event loop chạy
        4. Parse JSON {code, data}

        Lưu ý: KHÔNG dùng threading.Event.wait() hay page.route() bên trong
        sync_playwright — cả hai đều block event loop / làm gián đoạn reCAPTCHA.
        """
        import json as _json
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

        captured_body: list = []  # [str] khi response đến

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                locale="vi-VN",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()

            # Listener — gọi trong Playwright event loop (an toàn)
            def _on_resp(resp):
                if "ListWarantyInfo" in resp.url or \
                   "listwarantyinfo" in resp.url.lower():
                    try:
                        captured_body.append(resp.text())
                    except Exception:
                        captured_body.append("")

            page.on("response", _on_resp)

            # Mở trang bảo hành
            page.goto(WARRANTY_PAGE, wait_until="domcontentloaded", timeout=30000)

            # Đợi input keyword xuất hiện
            try:
                page.wait_for_selector("input[name='keyword']", timeout=15000)
            except PwTimeout:
                browser.close()
                raise RuntimeError("Trang bảo hành không load được form")

            # Đợi reCAPTCHA load xong trước khi submit
            try:
                page.wait_for_function(
                    "typeof grecaptcha !== 'undefined' && "
                    "typeof grecaptcha.execute === 'function'",
                    timeout=10000,
                )
            except PwTimeout:
                pass  # tiếp tục dù reCAPTCHA chưa load — có thể vẫn hoạt động

            # Set search_type + fill keyword
            page.evaluate(
                "() => { var el = document.querySelector(\"input[name='type']\"); "
                f"if(el) el.value = '{search_type}'; }}"
            )
            page.fill("input[name='keyword']", keyword)
            page.wait_for_timeout(300)  # nhỏ delay để JS ổn định

            # Click nút KIỂM TRA
            for btn_sel in ["button.submitSearch", "button.submit",
                            "button[type='submit']"]:
                el = page.query_selector(btn_sel)
                if el:
                    el.click()
                    break
            else:
                page.press("input[name='keyword']", "Enter")

            # Đợi network idle — cách đáng tin cậy nhất để bắt XHR response
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PwTimeout:
                pass  # timeout OK — response có thể đã về rồi

            browser.close()

        if not captured_body:
            result.need_browser = True
            result.error = "TGDD không phản hồi — thử mở trình duyệt"
            return

        body = captured_body[0]
        try:
            js = _json.loads(body)
        except Exception:
            self._parse(body, result)
            return

        code = js.get("code")
        if code == 200:
            self._parse(js.get("data", ""), result)
        elif code == 201:
            result.need_browser = True
            result.error = "TGDD yêu cầu xác minh số điện thoại"
        elif code == 502:
            result.error = "TGDD đang bảo trì"
        elif code is not None:
            result.error = js.get("errormessage") or f"Lỗi code {code}"
        else:
            self._parse(body, result)

    # ── HTML parsing ──────────────────────────────────────────────────────────

    def _parse(self, html: str, result: WarrantyResult):
        soup = BeautifulSoup(html, "html.parser")

        no_result = soup.find(class_=lambda c: c and "no-result" in c)
        if no_result:
            result.raw_message = no_result.get_text(strip=True)
            result.success = True
            return

        error_el = soup.find(class_=lambda c: c and "error" in str(c).lower())
        if error_el and not soup.find(class_="warranty-item"):
            result.raw_message = error_el.get_text(strip=True)
            result.success = True
            return

        for item_el in soup.find_all(class_=lambda c: c and (
            "warranty-item" in str(c) or "item-warr" in str(c) or
            "prod-item" in str(c) or "warrantyItem" in str(c)
        )):
            result.items.append(self._parse_item(item_el))

        if not result.items:
            for row in soup.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 3:
                    item = WarrantyItem()
                    texts = [c.get_text(strip=True) for c in cells]
                    item.product_name    = texts[0]
                    item.serial          = texts[1] if len(texts) > 1 else ""
                    item.warranty_end    = texts[2] if len(texts) > 2 else ""
                    item.warranty_status = texts[3] if len(texts) > 3 else ""
                    item.status_color    = _status_color(item.warranty_status)
                    result.items.append(item)

        if not result.items:
            body = soup.get_text(separator=" ", strip=True)
            result.raw_message = body[:400] if body else "Không có dữ liệu"

        result.success = True

    def _parse_item(self, el) -> WarrantyItem:
        item = WarrantyItem()
        text = el.get_text(separator="|", strip=True)

        def _field(labels: list[str]) -> str:
            for lbl in labels:
                tag = el.find(string=lambda s: s and lbl.lower() in s.lower())
                if tag:
                    parent = tag.parent
                    nxt = parent.find_next_sibling()
                    if nxt:
                        return nxt.get_text(strip=True)
                    full = parent.get_text(strip=True)
                    after = full.split(":", 1)
                    if len(after) > 1:
                        return after[1].strip()
            return ""

        item.product_name    = _field(["tên sản phẩm", "sản phẩm", "product"])
        item.serial          = _field(["serial", "số serial", "mã serial"])
        item.imei            = _field(["imei"])
        item.purchase_date   = _field(["ngày mua", "purchase", "mua hàng"])
        item.warranty_end    = _field(["hết bảo hành", "ngày hết", "end", "kết thúc"])
        item.warranty_status = _field(["trạng thái", "status", "bảo hành"])
        item.store           = _field(["cửa hàng", "nơi mua", "store"])

        if not item.product_name and not item.warranty_status:
            item.raw_text = text[:200]

        item.status_color = _status_color(item.warranty_status or text)
        return item


def _status_color(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("còn bảo hành", "trong bảo hành", "hợp lệ", "active")):
        return "green"
    if any(k in t for k in ("hết bảo hành", "expired", "hết hạn")):
        return "red"
    if any(k in t for k in ("sắp hết", "gần hết", "warning")):
        return "yellow"
    return "dim"
