@echo off
title WiFi Auto-Reconnect
echo =============================================
echo   WiFi Auto-Reconnect for Awing Captive Portal
echo =============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python khong duoc cai dat!
    echo Vui long tai Python tu: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install required packages
echo [INFO] Dang kiem tra va cai dat thu vien can thiet...
pip install requests --quiet

echo.
echo [INFO] Dang khoi dong script...
echo [INFO] Nhan Ctrl+C de dung
echo.

:: Run the script
python wifi_auto_connect.py

pause
