# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file cho O2O Laptop Inspection
# Chạy: pyinstaller O2O_Inspection.spec

import sys

block_cipher = None

a = Analysis(
    ['scanner_ui.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Windows WMI
        'wmi',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'win32api',
        'win32con',
        # QR Code
        'qrcode',
        'qrcode.image',
        'qrcode.image.base',
        'qrcode.image.pure',
        'qrcode.image.pil',
        'qrcode.constants',
        'qrcode.exceptions',
        'qrcode.main',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL._tkinter_finder',
        # psutil
        'psutil',
        'psutil._pswindows',
        # SSL / certifi
        'certifi',
        'ssl',
        # tkinter (đảm bảo bundled)
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'IPython', 'jupyter', 'notebook',
        'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='O2O_Inspection',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # nén file, giảm size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # không hiện cửa sổ CMD đen
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # bỏ comment nếu có file icon
)
