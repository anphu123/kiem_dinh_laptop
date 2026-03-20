"""
Load cấu hình từ file .env (nằm cùng thư mục với executable).
Fallback về biến môi trường hệ thống nếu không có .env.
"""

import os

def _load_env():
    """Parse file .env đơn giản, không cần thư viện ngoài."""
    env_paths = [
        # Cùng thư mục với script / exe
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        # Thư mục chứa executable (khi build bằng PyInstaller)
        os.path.join(os.path.dirname(os.path.abspath(
            getattr(__import__("sys"), "executable", __file__)
        )), ".env"),
    ]
    for path in env_paths:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
            break

_load_env()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
