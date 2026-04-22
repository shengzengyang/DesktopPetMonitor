@echo off
chcp 65001 > nul
cd /d %~dp0

echo ==========================================
echo   Desktop Pet Monitor  -  Build to EXE
echo ==========================================

if not exist venv (
    echo [1/4] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip > nul
pip install -r requirements.txt
pip install pyinstaller

echo [3/4] Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [4/4] Building EXE (using DesktopPet.spec, bundles assets)...
pyinstaller --noconfirm --clean DesktopPet.spec

echo.
if exist dist\DesktopPet.exe (
    echo Build succeeded: dist\DesktopPet.exe
    for %%I in (dist\DesktopPet.exe) do echo Size: %%~zI bytes
) else (
    echo Build failed, check log above.
)

if /I "%1"=="--no-pause" goto :eof
pause
