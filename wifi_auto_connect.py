#!/usr/bin/env python3
"""
High-Performance WiFi Auto-Reconnect
Tối ưu hóa tốc độ kết nối bằng Session Keep-Alive và Socket Check
"""

import requests
import time
import subprocess
import re
import socket # Dùng cái này check mạng nhanh hơn requests nhiều
from datetime import datetime
import ipaddress
import os
import sys

# ============ CẤU HÌNH ============
CONFIG = {
    "username": "awing15-15",
    "password": "Awing15-15@2023",
    "auth_url": "http://192.168.200.1/goform/login",
    "logout_url": "http://192.168.200.1/goform/logout", # Hardcode luôn cho nhanh
    "success_url": "http://v1.awingconnect.vn/Success",
    "session_duration": 15 * 60, 
    "gateway_ip": "192.168.200.1"
}

NETWORK = ipaddress.ip_network("192.168.200.0/21")

# Tạo một Session toàn cục để tái sử dụng kết nối TCP (Keep-Alive)
# Đây là chìa khóa để login nhanh
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection": "keep-alive" # Bắt buộc giữ kết nối
})

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifi_fast_log.txt")

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3] # Lấy cả mili giây
    log_line = f"[{timestamp}] [{level}] {message}"
    try:
        if sys.stdout and sys.stdout.isatty():
            print(log_line)
    except: pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except: pass

def fast_check_internet():
    """
    Check internet siêu tốc bằng cách ping tới Google DNS (8.8.8.8) qua cổng 53.
    Không dùng HTTP request để tránh tốn thời gian tải trang.
    """
    try:
        # Timeout cực ngắn: 1 giây
        socket.setdefaulttimeout(1)
        # Thử mở kết nối tới 8.8.8.8 port 53 (DNS)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        s.close()
        return True
    except Exception:
        return False

def get_current_ip():
    """Lấy IP hiện tại (đã tối ưu cờ ẩn window)"""
    try:
        startupinfo = None
        creation_flags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creation_flags = 0x08000000

        result = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore",
            creationflags=creation_flags, startupinfo=startupinfo
        )
        
        # Regex tìm IP nhanh gọn
        match = re.search(r"IPv4Address.+: (192\.168\.20\d\.\d+)", result.stdout.replace("\r", "").replace("\n", ""))
        # Fallback regex nếu format khác
        if not match:
             match = re.search(r"(192\.168\.\d+\.\d+)", result.stdout)
             
        if match: return match.group(1)
    except: pass
    return None

def wait_for_correct_network():
    """Chờ kết nối đúng mạng"""
    log("📡 Đang đợi mạng 192.168.200.x...", "WAIT")
    while True:
        ip = get_current_ip()
        if ip:
            try:
                if ipaddress.ip_address(ip) in NETWORK:
                    log(f"✅ Đã vào mạng: {ip}")
                    return ip
            except: pass
        time.sleep(2)

def perform_cycle():
    """Chu trình Logout -> Login tối ưu"""
    log("🔄 Bắt đầu chu trình làm mới...")
    t_start = time.time()

    # 1. LOGOUT
    try:
        # Dùng session.get thay vì requests.get để tận dụng keep-alive
        session.get(CONFIG["logout_url"], timeout=2)
    except Exception as e:
        log(f"Lỗi logout nhẹ (kệ nó): {e}", "WARN")

    t_logout = time.time()
    
    # 2. LOGIN
    auth_data = {
        "username": CONFIG["username"],
        "password": CONFIG["password"],
        "dst": CONFIG["success_url"],
        "popup": "false",
    }
    
    try:
        # Gửi POST ngay lập tức trên cùng session
        resp = session.post(CONFIG["auth_url"], data=auth_data, timeout=5)
        t_login = time.time()
        
        # Phân tích kết quả dựa trên HTTP Code luôn, khoan check internet vội
        # Gateway thường trả về 200 hoặc 302 nếu thành công
        if resp.status_code < 400:
            log(f"🚀 Đã gửi Login, tái kết nối trong: {(t_login - t_start):.3f}s (Logout: {t_logout - t_start:.3f}s | Login: {t_login - t_logout:.3f}s)")
        else:
            log(f"❌ Login thất bại. Code: {resp.status_code}", "ERROR")
            return False

    except Exception as e:
        log(f"❌ Exception: {e}", "ERROR")
        return False

def main():
    log("🚀 SPEED OPTIMIZED SCRIPT STARTED")
    
    # Check mạng lần đầu
    wait_for_correct_network()
    
    if fast_check_internet():
        log("Đã có mạng, logout session cũ để reset đồng hồ.")
        session.get(CONFIG["logout_url"])
    
    perform_cycle()

    while True:
        try:
            # Ngủ 14 phút 55 giây (Sát nút hơn để tận dụng tối đa)
            # Vì quá trình reconnect giờ chỉ mất < 0.5s nên không cần trừ hao quá nhiều
            sleep_time = CONFIG["session_duration"] - 60 
            
            # Tính toán thời gian thức dậy chính xác
            wake_up_time = datetime.fromtimestamp(time.time() + sleep_time).strftime('%H:%M:%S')
            log(f"💤 Ngủ đông đến {wake_up_time} (còn {sleep_time}s)...")
            
            time.sleep(sleep_time)

            # Kiểm tra xem còn kết nối WiFi không trước khi làm
            current_ip = get_current_ip()
            if not current_ip or ipaddress.ip_address(current_ip) not in NETWORK:
                log("⚠️ Mất kết nối WiFi lúc ngủ, đợi kết nối lại...")
                wait_for_correct_network()

            # THỰC HIỆN RECONNECT
            perform_cycle()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Crash loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()