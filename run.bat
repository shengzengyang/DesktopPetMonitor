@echo off
chcp 65001 > nul
cd /d %~dp0

if not exist venv (
    echo [1/2] 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo [2/2] 启动桌宠...
pythonw main.py
