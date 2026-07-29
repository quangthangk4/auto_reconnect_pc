#!/usr/bin/env python3
"""
High-Performance WiFi Auto-Reconnect V2
Cơ chế: Dynamic Password Harvesting (Tự động lấy mật khẩu động từ API)
"""

import requests
from requests.adapters import HTTPAdapter
import time
import re
import sys
import socket
from urllib.parse import urlencode
from datetime import datetime

# ============ CẤU HÌNH ============
CONFIG = {
    "default_username": "awing15-15",
    "gateway_url":      "http://192.168.200.1/login",
    "api_verify_url":   "http://v1.awingconnect.vn/Home/VerifyUrl",
    "check_url":        "http://www.google.com/generate_204",
}

# Session toàn cục
session = requests.Session()
session.headers.update({
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection":      "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Accept":          "*/*",
})

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}")

def logkv(key, value):
    sys.stdout.write(f"\r[{ts()}] {key}: {value}        ")
    sys.stdout.flush()

def get_dynamic_credentials():
    # Step 1: Lấy CHAP params từ gateway
    log("  [1/3] GET gateway login page...")
    t1 = time.time()
    html_body = None
    for attempt in range(6):
        try:
            session.mount("http://", HTTPAdapter())  # fresh TCP mỗi lần thử
            resp = session.get(CONFIG["gateway_url"], allow_redirects=False, timeout=(1.5, 2))
            log(f"  [1/3] HTTP Status: {resp.status_code}")
            log(f"  [1/3] Response Headers: {dict(resp.headers)}")
            html_body = resp.content.decode("utf-8", errors="ignore")
            log(f"  [1/3] Response Body (Snippet):\n{html_body[:500]}\n---")
            break
        except Exception as e:
            log(f"  [1/3] Attempt {attempt+1} error: {e}")
            if attempt < 5:
                time.sleep(0.3)

    if html_body is None:
        log(f"  [1/3] ❌ Gateway không phản hồi sau 6 lần thử ({(time.time()-t1)*1000:.0f}ms)")
        return None, None

    serial         = re.search(r'id="serial" value="([^"]*)"', html_body)
    client_mac     = re.search(r'id="client_mac" value="([^"]*)"', html_body)
    client_ip      = re.search(r'id="client_ip" value="([^"]*)"', html_body)
    login_url      = re.search(r'id="login_url" value="([^"]*)"', html_body)
    chap_id        = re.search(r'id="chap-id" value="([^"]*)"', html_body)
    chap_challenge = re.search(r'id="chap-challenge" value="([^"]*)"', html_body)

    log(f"  [1/3] Extracted CHAP Raw Params:")
    log(f"        serial: {serial.group(1) if serial else None}")
    log(f"        client_mac: {client_mac.group(1) if client_mac else None}")
    log(f"        client_ip: {client_ip.group(1) if client_ip else None}")
    log(f"        login_url: {login_url.group(1) if login_url else None}")
    log(f"        chap_id: {chap_id.group(1) if chap_id else None}")
    log(f"        chap_challenge: {chap_challenge.group(1) if chap_challenge else None}")

    if not (serial and client_mac and client_ip and chap_id and chap_challenge):
        log("  [1/3] ❌ Không parse được CHAP params")
        return None, None

    params = {
        "serial":         serial.group(1),
        "client_mac":     client_mac.group(1),
        "client_ip":      client_ip.group(1),
        "userurl":        "",
        "login_url":      login_url.group(1) if login_url else CONFIG["gateway_url"],
        "chap_id":        chap_id.group(1),
        "chap_challenge": chap_challenge.group(1),
    }
    full_login_url = f"http://v1.awingconnect.vn/login?{urlencode(params)}"
    log(f"  [1/3] Full login URL: {full_login_url}")
    log(f"  [1/3] ✅ CHAP params OK ({(time.time()-t1)*1000:.0f}ms)")

    # Step 2: Lấy dynamic credentials từ VerifyUrl
    log("  [2/3] POST VerifyUrl...")
    t2 = time.time()
    resp_api = session.post(
        CONFIG["api_verify_url"],
        headers={
            "Host":         "v1.awingconnect.vn",
            "Referer":      full_login_url,
            "Content-Type": "application/json",
        },
        json={},
        timeout=10,
    )

    log(f"  [2/3] HTTP Status: {resp_api.status_code}")
    log(f"  [2/3] Response Headers: {dict(resp_api.headers)}")

    try:
        data = resp_api.json()
        log(f"  [2/3] Response JSON:\n{data}\n---")
    except Exception:
        log(f"  [2/3] ❌ Response không phải JSON: {resp_api.text}")
        return None, None

    html_content = data.get("captiveContext", {}).get("contentAuthenForm", "")
    log(f"  [2/3] Form HTML content from JSON:\n{html_content}\n---")

    user_match = re.search(r'name="username"\s+value="([^"]+)"', html_content)
    pass_match = re.search(r'name="password"\s+value="([^"]+)"', html_content)

    username_val = user_match.group(1) if user_match else CONFIG.get("default_username")
    password_val = pass_match.group(1) if pass_match else None

    if not password_val:
        log("  [2/3] ❌ Không tìm thấy password trong JSON")
        return None, None

    log(f"  [2/3] Extracted username: {username_val}")
    log(f"  [2/3] Extracted password: {password_val}")
    log(f"  [2/3] ✅ Credentials OK ({(time.time()-t2)*1000:.0f}ms)")
    return username_val, password_val


def perform_login_cycle():
    t_start = time.time()
    log(">>> Bắt đầu login cycle")
    # Clear connection pool — tránh reuse TCP connection cũ đã chết sau khi WiFi drop
    session.mount("http://", HTTPAdapter())

    try:
        username, password = get_dynamic_credentials()
    except Exception as e:
        log(f"  ❌ Exception lấy credentials: {e}")
        return False

    if not username or not password:
        log("  ❌ Hủy login — không lấy được credentials (username/password)")
        return False

    # Step 3: POST login về gateway
    log("  [3/3] POST login gateway...")
    t3 = time.time()
    post_payload = {
        "username": username,
        "password": password,
        "dst":      "http://v1.awingconnect.vn/Success",
        "popup":    "false",
    }
    log(f"  [3/3] Target URL: {CONFIG['gateway_url']}")
    log(f"  [3/3] Payload POST: {post_payload}")
    try:
        resp = session.post(
            CONFIG["gateway_url"],
            data=post_payload,
            timeout=5,
        )
    except Exception as e:
        log(f"  [3/3] ❌ Exception: {e}")
        return False

    duration = time.time() - t_start
    log(f"  [3/3] HTTP Status: {resp.status_code}")
    log(f"  [3/3] Final URL: {resp.url}")
    log(f"  [3/3] Redirect History: {[r.url for r in resp.history]}")
    log(f"  [3/3] Response Headers: {dict(resp.headers)}")
    log(f"  [3/3] Response Body (Full/Snippet):\n{resp.text[:1000]}\n---")

    if resp.status_code < 400:
        log(f"  [3/3] ✅ Login OK ({(time.time()-t3)*1000:.0f}ms)")
        log(f">>> ✅ HOÀN THÀNH — tổng {duration*1000:.0f}ms")
        return True
    else:
        log(f"  [3/3] ❌ Gateway trả HTTP {resp.status_code}")
        return False


# Cache IP để tránh DNS lookup khi mất kết nối
CACHED_CHECK_IP = None

def get_check_ip():
    global CACHED_CHECK_IP
    if CACHED_CHECK_IP is None:
        try:
            CACHED_CHECK_IP = socket.gethostbyname("www.google.com")
        except Exception:
            pass
    return CACHED_CHECK_IP


def check_internet():
    ip = get_check_ip()
    if ip:
        url = f"http://{ip}/generate_204"
        headers = {"Host": "www.google.com"}
    else:
        url = CONFIG["check_url"]
        headers = {}

    try:
        r = requests.get(url, headers=headers, timeout=3)
        return r.status_code == 204
    except Exception:
        # Nếu mất mạng, xóa cache IP để đảm bảo phân giải mới khi kết nối lại
        global CACHED_CHECK_IP
        CACHED_CHECK_IP = None
        return False


def main():
    log("=== WiFi Auto-Reconnect started ===")
    t_lost = None
    while True:
        try:
            while True:
                if check_internet():
                    if t_lost is not None:
                        # Vừa có lại mạng — tính tổng downtime
                        downtime = time.time() - t_lost
                        log(f"🌐 Có mạng lại — downtime: {downtime:.1f}s")
                        t_lost = None
                    logkv("heartbeat", "alive")
                    time.sleep(1)
                else:
                    if t_lost is None:
                        t_lost = time.time()  # ghi nhận thời điểm mất mạng
                    print()  # xuống dòng sau logkv
                    log("⚠️  Mất kết nối! Đang login lại...")
                    if perform_login_cycle():
                        break
                    else:
                        log("⏳ Thử lại sau 5s...")
                        time.sleep(5)

        except KeyboardInterrupt:
            print()
            log("=== Dừng ===")
            break
        except Exception as e:
            log(f"❌ Crash: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()