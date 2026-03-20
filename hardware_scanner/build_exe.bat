@echo off
chcp 65001 > nul
echo ====================================================
echo   O2O Laptop Inspection - Build Windows EXE
echo ====================================================
echo.

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python. Tai tai: https://python.org
    pause & exit /b 1
)

echo [1/3] Cai dat thu vien...
pip install pyinstaller psutil "qrcode[pil]" wmi pywin32 -q --upgrade
if %errorlevel% neq 0 (
    echo [LOI] Cai dat thu vien that bai.
    pause & exit /b 1
)

echo [2/3] Build EXE tu spec file...
pyinstaller O2O_Inspection.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Build that bai. Xem log tren.
    pause & exit /b 1
)

echo [3/3] Hoan tat!
echo.
echo ====================================================
echo   FILE EXE: dist\O2O_Inspection.exe
echo ====================================================
echo.
echo   - Copy dist\O2O_Inspection.exe vao USB
echo   - Chay tren laptop Windows can test
echo   - Khong can cai Python
echo.
start dist\
pause
