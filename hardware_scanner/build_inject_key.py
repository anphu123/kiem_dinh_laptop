"""
Chạy lúc CI/CD build — KHÔNG chạy tay.
Đọc GEMINI_API_KEY từ environment variable (GitHub Secret),
XOR encode và ghi vào _embedded_key.py để PyInstaller bundle vào binary.
"""

import os
import sys

KEY   = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
SALT  = b"O2OLaptopInspection_S4lt#2025"

if not KEY:
    print("[WARNING] GEMINI_API_KEY không có trong environment — embedded key sẽ rỗng")

encoded = [b ^ SALT[i % len(SALT)] for i, b in enumerate(KEY.encode("utf-8"))]

out = f'''\
# Auto-generated at build time. DO NOT EDIT. DO NOT COMMIT.
_K = {encoded}
_S = {list(SALT)}
_M = "{MODEL}"
'''

with open("_embedded_key.py", "w", encoding="utf-8") as f:
    f.write(out)

print(f"[OK] _embedded_key.py generated ({len(encoded)} bytes encoded)")
