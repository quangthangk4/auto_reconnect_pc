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
    "trigger_url": "http://192.168.200.1/login", # Link mồi để lấy redirect
    "api_verify_url": "http://v1.awingconnect.vn/Home/VerifyUrl", # Link lấy password
    "auth_url": "http://authen.awingconnect.vn/login", # Link login cuối cùng
    "logout_url": "http://192.168.200.1/goform/logout",
    "success_check_url": "http://v1.awingconnect.vn/Success",
    
    "session_duration": 15 * 60, # 15 phút
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
        resp = session.get("http://192.168.200.1/login", allow_redirects=False, timeout=5)
        html_body = resp.content.decode("utf-8", errors="ignore")
        log(f"test: {html_body}")

        # Tìm các tham số hidden trong form
        serial_match = re.search(r'id="serial" value="([^"]*)"', html_body)
        client_mac_match = re.search(r'id="client_mac" value="([^"]*)"', html_body)
        client_ip_match = re.search(r'id="client_ip" value="([^"]*)"', html_body)
        login_url_match = re.search(r'id="login_url" value="([^"]*)"', html_body)
        chap_id_match = re.search(r'id="chap-id" value="([^"]*)"', html_body)
        chap_challenge_match = re.search(r'id="chap-challenge" value="([^"]*)"', html_body)

        if serial_match and client_mac_match and client_ip_match and chap_id_match and chap_challenge_match:
            serial = serial_match.group(1)
            client_mac = client_mac_match.group(1)
            client_ip = client_ip_match.group(1)
            login_url_gw = login_url_match.group(1) if login_url_match else "http://192.168.200.1/login"
            chap_id = chap_id_match.group(1)
            chap_challenge = chap_challenge_match.group(1)
            
            # Xây dựng URL thủ công theo yêu cầu
            # Lưu ý: Các giá trị chap cần được encode đúng cách nếu dùng thư viện, 
            # nhưng ở đây ta ghép chuỗi để giống format yêu cầu (giữ nguyên các ký tự escape nếu có trong value html)
            
            # Sử dụng urllib để encode các tham số an toàn
            from urllib.parse import urlencode
            
            params = {
                "serial": serial,
                "client_mac": client_mac,
                "client_ip": client_ip,
                "userurl": "",
                "login_url": login_url_gw,
                "chap_id": chap_id,
                "chap_challenge": chap_challenge
            }
            
            base_url = "http://v1.awingconnect.vn/login"
            full_login_url = f"{base_url}?{urlencode(params)}"
            
            log(f"✅ Đã tạo URL Login thủ công: {full_login_url}")
            
        else:
            log("❌ Không tìm thấy đủ thông tin (serial, mac, ip, chap...) để tạo URL", "ERROR")
            return None

        log(f"➡️ Redirect URL: {full_login_url}")
        
        # Headers giả lập (QUAN TRỌNG: Host phải là tên miền)
        headers = {
            "Host": "v1.awingconnect.vn", 
            "Referer": full_login_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }
        
        # Gọi POST
        resp_api = session.post(CONFIG["api_verify_url"], headers=headers, json={}, timeout=10)
        
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
    # try:
    #     session.get(CONFIG["logout_url"], timeout=1)
    # except: pass

    dynamic_password = get_dynamic_password()
    
    if not dynamic_password:
        log("⛔ Không lấy được mật khẩu, hủy login.", "ERROR")
        return False

    # 3. Gửi Request Login cuối cùng
    auth_data = {
        "username": "awing15-15",
        "password": dynamic_password, # Sử dụng pass vừa lấy
        "dst": "http://v1.awingconnect.vn/Success",
        "popup": "false",
    }

    try:
        resp = session.post("http://192.168.200.1/login", data=auth_data, timeout=5)
        
        # Check kết quả (302 redirect hoặc 200 OK trả về trang Success)
        if resp.status_code < 400:
            log(f"tra ve: {resp.status_code}")
            duration = time.time() - t_start
            log(f"🚀 LOGIN THÀNH CÔNG! Tổng thời gian: {duration:.3f}s")
            return True
        else:
            log(f"❌ Login thất bại. HTTP Code: {resp.status_code}", "ERROR")
            return False

    except Exception as e:
        log(f"❌ Exception Login: {e}", "ERROR")
        return False

def check_internet():
    try:
        # Kiểm tra kết nối đến Google DNS (8.8.8.8) cổng 53
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def main():
    # Login lần đầu khi chạy script
    perform_login_cycle()

    while True:
        try:
            # Thời gian ngủ "an toàn" (14 phút)
            sleep_time = 840 
            
            wake_up_time = datetime.fromtimestamp(time.time() + sleep_time).strftime('%H:%M:%S')
            log(f"💤 WiFi OK. Ngủ đông đến {wake_up_time} (còn {sleep_time}s)...")
            log(f"="*50)
            
            time.sleep(sleep_time)
            
            log("👀 Hết thời gian ngủ đông, bắt đầu theo dõi kết nối mạng liên tục...")
            
            # Vòng lặp check mạng liên tục
            while True:
                if check_internet():
                    # Vẫn có mạng, check lại sau 1s để phản ứng nhanh nhất có thể
                    time.sleep(1)
                else:
                    # Mất mạng -> Login lại ngay
                    log("⚠️ Phát hiện mất kết nối Internet! Đang login lại...", "WARNING")
                    if perform_login_cycle():
                        # Nếu login thành công, thoát vòng lặp check để quay lại ngủ 840s
                        break
                    else:
                        # Login thất bại, chờ 5s rồi thử lại (vẫn giữ trạng thái check)
                        time.sleep(5)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Crash loop: {e}", "ERROR")
            time.sleep(5)

if __name__ == "__main__":
    main()