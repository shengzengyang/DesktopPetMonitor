@echo off
chcp 65001 > nul
cd /d %~dp0

echo ==========================================
echo   Desktop Pet Monitor  -  Build to EXE
echo ==========================================

if not exist venv (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/4] 安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [3/4] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist DesktopPet.spec del /q DesktopPet.spec

echo [4/4] 打包 EXE...
pyinstaller --noconfirm --onefile --windowed ^
    --name "DesktopPet" ^
    --hidden-import pynvml ^
    main.py

echo.
if exist dist\DesktopPet.exe (
    echo 构建成功: dist\DesktopPet.exe
) else (
    echo 构建失败, 请检查上方日志.
)
pause
