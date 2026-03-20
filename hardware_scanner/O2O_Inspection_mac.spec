# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file cho macOS (.app bundle)
# Chạy: pyinstaller O2O_Inspection_mac.spec

block_cipher = None

a = Analysis(
    ['scanner_ui.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
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
        # psutil macOS
        'psutil',
        'psutil._psmacosx',
        'psutil._psposix',
        'psutil._common',
        # tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        # plistlib (dùng để đọc diskutil)
        'plistlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Loại bỏ các module Windows
        'wmi', 'win32com', 'win32api', 'win32con', 'pywintypes',
        # Loại bỏ lib nặng không cần
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'IPython', 'jupyter', 'notebook',
        'test', 'unittest',
    ],
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
    upx=False,  # macOS không dùng UPX tốt
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.icns',
)

# Tạo .app bundle
app = BUNDLE(
    exe,
    name='O2O_Inspection.app',
    icon=None,
    bundle_identifier='com.o2o.laptop-inspection',
    info_plist={
        'CFBundleName': 'O2O Inspection',
        'CFBundleDisplayName': 'O2O Laptop Inspection',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # hỗ trợ Dark Mode
    },
)
