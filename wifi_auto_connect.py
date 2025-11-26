#!/usr/bin/env python3
"""
WiFi Auto-Reconnect Script for Awing Captive Portal
Tự động kết nối lại WiFi miễn phí khi hết 15 phút

Author: Claude
Usage: python wifi_auto_connect.py
"""

import requests
import time
import subprocess
import re
import uuid
from datetime import datetime
from urllib.parse import urlencode
import ipaddress

# ============ CẤU HÌNH ============


CONFIG = {
    "client_mac": "",
    # Thông tin đăng nhập (từ captive portal)
    "username": "awing15-15",
    "password": "Awing15-15@2023",

    "auth_url": "http://authen.awingconnect.vn/login",
    "success_url": "http://v1.awingconnect.vn/Success",
    
    # Timing
    "session_duration": 15 * 60, # 15 phút = 900 giây
}

NETWORK = ipaddress.ip_network("192.168.200.0/21")

# ============ HEADERS ============
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


import os

# Log file path (cùng thư mục với script)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifi_log.txt")

def get_wifi_mac():
    result = subprocess.run(
        ["getmac", "/v", "/fo", "list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    sections = result.stdout.split("\n\n")
    for sec in sections:
        if "Wi-Fi" in sec or "Wireless" in sec:
            for line in sec.splitlines():
                if "Physical Address" in line:
                    mac = line.split(":", 1)[1].strip()
                    mac_colon = mac.replace("-", ":")
                    return mac_colon
    return None

def log(message, level="INFO"):
    """In log với timestamp - ghi ra cả console (nếu có) và file"""


    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"

    # Chỉ print nếu đang có console (chạy bằng python.exe trong CMD)
    try:
        if sys.stdout and sys.stdout.isatty():
            print(log_line)
    except Exception:
        pass

    # Ghi ra file log
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except:
        pass



def check_internet():
    """Kiểm tra có internet hay không"""
    test_urls = [
        "http://www.google.com",
        "http://www.msftconnecttest.com/connecttest.txt",
        "http://captive.apple.com",
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5, allow_redirects=False)
            # Nếu bị redirect về captive portal thì không có internet
            if response.status_code == 200:
                return True
            elif response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get("Location", "")
                if "awingconnect" in location or "captive" in location.lower():
                    return False
        except requests.exceptions.RequestException:
            continue
    
    return False


def get_current_ip():
    """Lấy IP hiện tại từ adapter WiFi - KHÔNG HIỆN CỬA SỔ"""
    try:
        # --- PHẦN SỬA ĐỔI ---
        # Cấu hình để không hiện cửa sổ console đen khi gọi lệnh ipconfig
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # Windows command với cờ ngăn hiển thị window (CREATE_NO_WINDOW = 0x08000000)
        creation_flags = 0x08000000 if os.name == 'nt' else 0

        result = subprocess.run(
            ["ipconfig"], 
            capture_output=True, 
            text=True, 
            encoding="utf-8",
            errors="ignore",
            creationflags=creation_flags, # <-- THÊM DÒNG NÀY
            startupinfo=startupinfo       # <-- VÀ DÒNG NÀY (để chắc chắn)
        )
        # --------------------
        
        # (Giữ nguyên phần xử lý bên dưới của bạn)
        lines = result.stdout.split("\n")
        in_wifi_section = False
        
        for line in lines:
            if "Wi-Fi" in line or "Wireless" in line:
                in_wifi_section = True
            elif "Ethernet" in line or "adapter" in line.lower():
                in_wifi_section = False
            
            if in_wifi_section and "IPv4" in line:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if match:
                    return match.group(1)
        
        # Fallback
        for line in lines:
            if "192.168" in line:
                match = re.search(r"(192\.168\.\d+\.\d+)", line)
                if match:
                    return match.group(1)
                    
    except Exception as e:
        log(f"Không lấy được IP: {e}", "WARNING")
    
    return None

def check_correct_network():
    current_ip = get_current_ip()
    if current_ip is None:
        return False, None

    try:
        ip_obj = ipaddress.ip_address(current_ip)
        is_correct = ip_obj in NETWORK
        return is_correct, current_ip
    except ValueError:
        # IP không hợp lệ
        return False, current_ip


def wait_for_correct_network():
    """
    Đợi cho đến khi người dùng kết nối đúng mạng WiFi
    Check mỗi 5 giây
    """
    log("=" * 50)
    log("⚠️  ĐANG ĐỢI KẾT NỐI ĐÚNG MẠNG WIFI...")
    log(f"   Cần IP bắt đầu bằng: {NETWORK}")
    log("=" * 50)
    
    check_count = 0
    while True:
        is_correct, current_ip = check_correct_network()
        check_count += 1
        
        if is_correct:
            log(f"✅ Đã kết nối đúng mạng! IP: {current_ip}")
            return current_ip
        else:
            if current_ip:
                log(f"❌ Sai mạng! IP hiện tại: {current_ip} (cần {NETWORK}) - Check #{check_count}")
            else:
                log(f"❌ Không tìm thấy IP WiFi - Chưa kết nối WiFi? - Check #{check_count}")
            
            # Gợi ý cho người dùng
            if check_count % 2 == 0:  # Mỗi 30 giây nhắc 1 lần
                log("💡 Vui lòng kết nối WiFi đúng mạng (INET-Free WiFi)...")
            
            time.sleep(5)


def login():
    try:
        auth_data = {
            "username": CONFIG["username"],
            "password": CONFIG["password"],
            "dst": CONFIG["success_url"],
            "popup": "false",
        }
        
        requests.post(CONFIG["auth_url"], data=auth_data, headers=HEADERS, timeout=10)
        
        if check_internet():
            log("✅ KẾT NỐI THÀNH CÔNG!", "SUCCESS")
            return True
        else:
            log("⚠️ Đã gọi API nhưng chưa có internet", "WARNING")
            retry = 0
            while retry < 3 and not check_internet():
                retry += 1
                log(f"🔁 Thử login lại lần {retry}...")
                if login():
                    log("✅ Login thành công sau retry.")
                    return True
                time.sleep(1)
            return False
            
    except requests.exceptions.RequestException as e:
        log(f"❌ Lỗi kết nối: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"❌ Lỗi không xác định: {e}", "ERROR")
        return False
    

def awing_logout():
    """Logout session Awing trên gateway bằng MAC hiện tại."""
    try:
        gateway_ip = "192.168.200.1"  # Default Gateway của bạn
        logout_url = f"http://{gateway_ip}/goform/logout"
        params = {
            "mac": CONFIG["client_mac"]  # dùng luôn MAC trong CONFIG
        }

        resp = requests.get(
            logout_url,
            params=params,
            headers=HEADERS,
            timeout=5
        )


        if resp.status_code in (200, 301, 302):
            log("✅ Logout session thành công trên gateway.")
            return True
        else:
            log("⚠️ Logout trả về mã lạ, có thể vẫn OK nhưng không chắc.", "WARNING")
            return False

    except Exception as e:
        log(f"❌ Lỗi khi logout Awing: {e}", "ERROR")
        return False


def main():
    log("=" * 50)
    log("🚀 WIFI AUTO-RECONNECT SCRIPT STARTED")
    log(f"   MAC Address: {CONFIG['client_mac']}")
    log(f"   Expected IP: {NETWORK}")
    log(f"   Session duration: {CONFIG['session_duration']}s (15 phút)")
    log("   Strategy: Nếu đang có net → logout session cũ, sau đó mỗi ~15 phút chủ động logout + login để reset session.")
    log("=" * 50)


    mac_colon = get_wifi_mac()
    if mac_colon:
        CONFIG["client_mac"] = mac_colon
        log(f"🔧 Auto-detected MAC: {mac_colon}")
    else:
        log("⚠️ Không tự lấy được MAC, dùng giá trị hard-code trong CONFIG.", "WARNING")

    
    # Bước 0: Đợi kết nối đúng mạng
    wait_for_correct_network()
    
    # Bước 1: Nếu đã có internet → logout session cũ cho sạch
    log("🔍 Kiểm tra kết nối ban đầu...")
    if check_internet():
        log("✅ Đã có internet sẵn → chủ động logout session cũ.")
        awing_logout()
        time.sleep(2)  # cho gateway xử lý
    else:
        log("❌ Chưa có internet, không cần logout.")


    # Bước 2: Login lần đầu bằng script
    while True:
        if login():
            log("✅ Login ban đầu thành công, bắt đầu vòng refresh định kỳ.")
            break
        else:
            log("⚠️ Login ban đầu thất bại, thử lại sau 10 giây...")
            time.sleep(10)
    
    while True:
        try:
            # Đảm bảo vẫn đang ở đúng mạng
            is_correct, current_ip = check_correct_network()
            if not is_correct:
                log(f"⚠️ Phát hiện đã chuyển mạng (IP hiện tại: {current_ip}), đợi lại đúng WiFi...")
                wait_for_correct_network()
                
            # Ngủ gần hết session, trừ đi margin cho an toàn (vd 30s)
            safety_margin = 60  # bạn thích thì chỉnh 20–60 giây
            sleep_duration = CONFIG["session_duration"] - safety_margin
            if sleep_duration < 0:
                sleep_duration = 0

            log(f"😴 Ngủ {sleep_duration // 60} phút {sleep_duration % 60} giây trước khi refresh session...")
            log(f" (Sẽ check lại lúc {time.strftime('%H:%M:%S', time.localtime(time.time() + sleep_duration))})")
            time.sleep(sleep_duration)

            # Đến lúc refresh
            # ✅ LẤY MỐC THỜI GIAN TỪ ĐÂY
            start_reconnect = time.time()
            log("⏰ Đến hạn refresh session → logout + login lại.")
            awing_logout()

            if not login():
                log("❌ Login lại sau logout thất bại, thử lại với backoff...")
                # fallback: retry vài lần
                retry = 0
                while retry < 3 and not check_internet():
                    retry += 1
                    log(f"🔁 Thử login lại lần {retry}...")
                    if login():
                        log("✅ Login thành công sau retry.")
                        break
                    time.sleep(1)

            if check_internet():
                elapsed = time.time() - start_reconnect
                log(f"⏱ Thời gian từ logout đến lúc có internet: {elapsed:.2f} giây", "INFO")
            else:
                log("⚠️ Sau refresh vẫn chưa có internet, sẽ thử lại ở vòng sau.", "WARNING")
            
        except KeyboardInterrupt:
            log("\n👋 Đã dừng script bởi người dùng")
            break
        except Exception as e:
            log(f"❌ Lỗi trong main loop: {e}", "ERROR")
            log("🔄 Thử kết nối lại sau 5 giây...")
            time.sleep(5)
            if not check_internet():
                login()


if __name__ == "__main__":
    # Test nhanh kết nối
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        log("🧪 Chạy test kết nối một lần...")
        login()
    elif len(sys.argv) > 1 and sys.argv[1] == "--mac":
        log("🧪 Chạy test get mac...")
        print(get_wifi_mac())
    elif len(sys.argv) > 1 and sys.argv[1] == "--disconnect":
        log("🧪 Chạy test disconnect...")
        awing_logout()
    else:
        main()
