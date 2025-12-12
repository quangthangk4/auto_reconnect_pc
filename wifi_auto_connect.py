#!/usr/bin/env python3
"""
High-Performance WiFi Auto-Reconnect V2
Cơ chế: Dynamic Password Harvesting (Tự động lấy mật khẩu động từ API)
"""

import requests
import time
import subprocess
import re
import socket
from datetime import datetime
import ipaddress
import os,html
import sys

# ============ CẤU HÌNH ============
CONFIG = {
    # Username này thường cố định theo thiết bị/account
    "username": "awing15-15", 
    # Password sẽ được lấy tự động, không cần hardcode nữa
    
    # URL Flow
    "trigger_url": "http://authen.awingconnect.vn/login", # Link mồi để lấy redirect
    "api_verify_url": "http://v1.awingconnect.vn/Home/VerifyUrl", # Link lấy password
    "auth_url": "http://authen.awingconnect.vn/login", # Link login cuối cùng
    "logout_url": "http://192.168.200.1/goform/logout",
    "success_check_url": "http://v1.awingconnect.vn/Success",
    
    "session_duration": 15 * 60, # 15 phút
    "gateway_ip": "192.168.200.1"
}

# Session toàn cục
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest", # Quan trọng để giả lập gọi API từ JS
    "Accept": "*/*"
})

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_line = f"[{timestamp}] [{level}] {message}"
    try:
        if sys.stdout and sys.stdout.isatty():
            print(log_line)
    except: pass

def get_dynamic_password():
    """
    Hàm quan trọng nhất:
    1. Truy cập trang login để lấy Redirect URL (chứa Session ID, MAC, IP).
    2. Gọi API VerifyUrl để lấy JSON.
    3. Parse JSON lấy password động.
    """
    try:
        # BƯỚC 1: GET REQUEST để lấy Session Cookie và Redirect URL
        # Gateway sẽ redirect từ authen -> v1.awingconnect.vn với 1 đống tham số
        log("🕵️ Đang lấy Session params...")
        resp = session.get("http://authen.awingconnect.vn/goform/login", allow_redirects=False)
        html_body = resp.content.decode("utf-8", errors="ignore")

        m = re.search(r'url=([^"\'> ]+)', html_body)
        if not m:
            log("❌ Không tìm thấy redirect URL", "ERROR")
            return

        full_login_url = html.unescape(m.group(1))

        log(f"➡️ Redirect URL: {full_login_url}")
        
        # BƯỚC 2: Gọi API VerifyUrl
        # Cần set Referer là cái URL dài ngoằng vừa lấy được thì Server mới chịu trả lời
        session.headers.update({"Referer": full_login_url})
        
        log("⚡ Gọi API VerifyUrl để lấy Password...")
        resp_api = session.post(CONFIG["api_verify_url"], json={}, timeout=5)
        
        if resp_api.status_code != 200:
            log(f"❌ API Error: {resp_api.status_code}", "ERROR")
            return None

        # BƯỚC 3: Parse JSON lấy Password
        data = resp_api.json()
        
        # Password nằm trong chuỗi HTML tại key ['captiveContext']['contentAuthenForm']
        html_content = data.get("captiveContext", {}).get("contentAuthenForm", "")
        
        # Dùng Regex móc password ra: name="password" value="XXXXXXXX"
        pass_match = re.search(r'name="password"\s+value="([^"]+)"', html_content)
        
        if pass_match:
            extracted_pass = pass_match.group(1)
            log(f"🔓 Đã trích xuất Password động: {extracted_pass}")
            return extracted_pass
        else:
            log("❌ Không tìm thấy pattern password trong JSON trả về.", "ERROR")
            return None

    except Exception as e:
        log(f"❌ Lỗi khi lấy dynamic password: {e}", "ERROR")
        return None

def perform_login_cycle():
    t_start = time.time()
    
    # 1. Logout (Optional nhưng tốt để clean session cũ)
    try:
        session.get(CONFIG["logout_url"], timeout=1)
    except: pass


    # 2. Lấy Password động
    dynamic_password = get_dynamic_password()
    
    if not dynamic_password:
        log("⛔ Không lấy được mật khẩu, hủy login.", "ERROR")
        return False

    # 3. Gửi Request Login cuối cùng
    auth_data = {
        "username": CONFIG["username"],
        "password": dynamic_password, # Sử dụng pass vừa lấy
        "dst": CONFIG["success_check_url"],
        "popup": "false",
    }

    try:
        # Reset Referer về mặc định hoặc authen
        session.headers.update({"Referer": "http://v1.awingconnect.vn/"})
        
        resp = session.post(CONFIG["auth_url"], data=auth_data, timeout=5)
        
        # Check kết quả (302 redirect hoặc 200 OK trả về trang Success)
        if resp.status_code < 400:
            duration = time.time() - t_start
            log(f"🚀 LOGIN THÀNH CÔNG! Tổng thời gian: {duration:.3f}s")
            return True
        else:
            log(f"❌ Login thất bại. HTTP Code: {resp.status_code}", "ERROR")
            return False

    except Exception as e:
        log(f"❌ Exception Login: {e}", "ERROR")
        return False

def main():
    perform_login_cycle()

    while True:
        try:
            # Vì quá trình reconnect giờ chỉ mất < 0.5s nên không cần trừ hao quá nhiều
            sleep_time = CONFIG["session_duration"] - 60 
            
            # Tính toán thời gian thức dậy chính xác
            wake_up_time = datetime.fromtimestamp(time.time() + sleep_time).strftime('%H:%M:%S')
            log(f"💤 Ngủ đông đến {wake_up_time} (còn {sleep_time}s)...")
            log(f"="*50)
            
            time.sleep(sleep_time)
            
            # THỰC HIỆN RECONNECT
            perform_login_cycle()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Crash loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()