"""
Ưu tiên load key theo thứ tự:
1. _embedded_key.py  — baked vào binary lúc build (ưu tiên cao nhất)
2. .env              — override cho dev / custom key
3. Environment var   — fallback hệ thống
"""

import os
import sys


def _load_env_file():
    """Parse file .env thủ công, không cần thư viện ngoài."""
    exe_dir = os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__
    ))
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(exe_dir, ".env"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break


def _decode_embedded() -> tuple[str, str]:
    """Giải mã key đã XOR-encode từ _embedded_key module."""
    try:
        import _embedded_key as _ek
        key = bytes(b ^ _ek._S[i % len(_ek._S)]
                    for i, b in enumerate(_ek._K)).decode("utf-8")
        return key, _ek._M
    except Exception:
        return "", ""


# ── Load theo thứ tự ưu tiên ──────────────────────────────────────────────────
_embedded_key, _embedded_model = _decode_embedded()   # 1. embedded (binary)
_load_env_file()                                       # 2. .env file (override)

GEMINI_API_KEY = _embedded_key or os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = _embedded_model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
