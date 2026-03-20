@echo off
chcp 65001 > nul
echo Kiem tra va cai thu vien...
pip install psutil "qrcode[pil]" wmi pywin32 -q

echo Dang chay O2O Inspection...
python scanner_ui.py
