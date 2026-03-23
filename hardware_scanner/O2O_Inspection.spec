# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('_embedded_key.py', '.'), ('checklist.json', '.')],
    hiddenimports=['_embedded_key', 'controllers.scan_controller', 'controllers.checklist_controller', 'controllers.pricing_controller', 'controllers.cam_mic_controller', 'models.hardware', 'models.checklist', 'models.pricing', 'gemini_pricer', 'scanner', 'cv2', 'sounddevice'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='O2O_Inspection',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
app = BUNDLE(
    exe,
    name='O2O_Inspection.app',
    icon='icon.icns',
    bundle_identifier=None,
)
