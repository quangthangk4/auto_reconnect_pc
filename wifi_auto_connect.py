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
    "trigger_url": "http://156.156.157.26/login?dst=www.msftconnecttest.com/redirect", # Link mồi để lấy redirect
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
    "Host":"authen.awingconnect.vn",
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
    try:
        # --- BƯỚC 1: Lấy Redirect URL từ Gateway ---
        # Gateway IP: 192.168.200.1
        log("🕵️ Đang lấy Session params từ Gateway...")
        
        # Gọi thẳng vào IP Gateway để tránh lỗi DNS
        resp = session.get(CONFIG["trigger_url"], allow_redirects=False, timeout=5)
        html_body = resp.content.decode("utf-8", errors="ignore")

        # Tìm URL redirect
        m = re.search(r'url=([^"\'> ]+)', html_body)
        if not m:
            # Fallback: Thử tìm trong Header nếu body không có
            if 'Location' in resp.headers:
                full_login_url = resp.headers['Location']
            else:
                log("❌ Không tìm thấy redirect URL ở Gateway", "ERROR")
                return None
        else:
            full_login_url = html.unescape(m.group(1))

        log(f"➡️ Redirect URL: {full_login_url}")
        
        # --- BƯỚC 2: Gọi API VerifyUrl bằng IP Cứng ---
        # IP thật của v1.awingconnect.vn là 1.52.48.205 (Lấy từ log web của bạn)
        # Chúng ta PHẢI dùng IP này, vì nếu dùng tên miền, Router sẽ chặn lại.
        
        REAL_SERVER_IP = "1.52.48.205" 
        API_PATH = "/Home/VerifyUrl"
        
        # URL để request (Dùng IP)
        target_url = f"http://{REAL_SERVER_IP}{API_PATH}"
        
        # Headers giả lập (QUAN TRỌNG: Host phải là tên miền)
        headers = {
            "Host": "v1.awingconnect.vn", 
            "Referer": full_login_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }
        
        log(f"⚡ Gọi API VerifyUrl qua IP {REAL_SERVER_IP}...")
        
        # Gọi POST
        resp_api = session.post(target_url, headers=headers, json={}, timeout=10)
        
        # --- BƯỚC 3: Debug và Parse JSON ---
        log(f"Status Code: {resp_api.status_code}")
        
        try:
            data = resp_api.json()
            # Nếu chạy đến đây là thành công JSON
        except Exception as e:
            # Nếu lỗi ở đây -> Server trả về HTML chứ không phải JSON
            log(f"❌ Lỗi format JSON! Server trả về: \n{resp_api.text[:200]}...", "ERROR")
            return None

        # Parse password từ JSON
        html_content = data.get("captiveContext", {}).get("contentAuthenForm", "")
        pass_match = re.search(r'name="password"\s+value="([^"]+)"', html_content)
        
        if pass_match:
            extracted_pass = pass_match.group(1)
            log(f"🔓 Đã trích xuất Password: {extracted_pass}")
            return extracted_pass
        else:
            log("❌ JSON OK nhưng không có password.", "ERROR")
            return None

    except Exception as e:
        log(f"❌ Exception: {e}", "ERROR")
        return None
    

def perform_login_cycle():
    t_start = time.time()
    
    # 1. Logout (Optional nhưng tốt để clean session cũ)
    try:
        session.get(CONFIG["logout_url"], timeout=1)
    except: pass

    while True:
        dynamic_password = get_dynamic_password()
        
        if not dynamic_password:
            log("⛔ Không lấy được mật khẩu, hủy login.", "ERROR")
            continue
        break

    # 3. Gửi Request Login cuối cùng
    auth_data = {
        "username": CONFIG["username"],
        "password": dynamic_password, # Sử dụng pass vừa lấy
        "popup": "false",
    }

    try:
        # Reset Referer về mặc định hoặc authen
        session.headers.update({"Referer": "http://v1.awingconnect.vn/"})
        
        resp = session.post("http://192.168.200.1/login", data=auth_data, timeout=5)
        
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