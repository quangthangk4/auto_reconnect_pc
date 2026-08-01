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
from urllib.parse import urlencode, quote, quote_from_bytes
from datetime import datetime

# ============ CẤU HÌNH ============
CONFIG = {
    "default_username":   "awing60",
    "gateway_url":        "http://186.186.0.1/login",
    "api_verify_url":     "http://v1.awingconnect.vn/Home/VerifyUrl",
    "check_url":          "http://186.186.0.1/logout",
    "logout_url":         "http://free.wi-mesh.vn/logout",
    "serial":             "4C:5E:0C:1C:00:67",
    "reconnect_interval": 840,  # 14 phút (14 * 60 giây)
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
            resp = session.get(CONFIG["gateway_url"], allow_redirects=True, timeout=(3, 5))
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

    # Parse các thông số từ đối tượng JS wifiInfo (Wi-Mesh SPA)
    m_mac       = re.search(r'["\']?mac["\']?\s*:\s*"([^"]*)"', html_body)
    m_ip        = re.search(r'["\']?ip["\']?\s*:\s*"([^"]*)"', html_body)
    m_login_only= re.search(r'["\']?link-login-only["\']?\s*:\s*"([^"]*)"', html_body)
    m_orig      = re.search(r'["\']?link-orig["\']?\s*:\s*"([^"]*)"', html_body)
    m_chap_id   = re.search(r'["\']?chap_id["\']?\s*:\s*"([^"]*)"', html_body)
    m_chap_ch   = re.search(r'["\']?chap_challenge["\']?\s*:\s*"([^"]*)"', html_body)
    m_serial    = re.search(r'["\']?serial["\']?\s*:\s*"([^"]*)"', html_body)

    serial_val         = m_serial.group(1) if m_serial else CONFIG.get("serial", "4C:5E:0C:1C:00:67")
    client_mac_val     = m_mac.group(1) if m_mac else None
    client_ip_val      = m_ip.group(1) if m_ip else None
    login_url_val      = m_login_only.group(1) if m_login_only else "http://free.wi-mesh.vn/login"
    userurl_val        = m_orig.group(1) if m_orig else CONFIG["gateway_url"]
    chap_id_val        = m_chap_id.group(1) if m_chap_id else None
    chap_challenge_val = m_chap_ch.group(1) if m_chap_ch else None

    # Chuẩn hóa raw escapes \\ -> \
    if chap_id_val:
        chap_id_val = chap_id_val.replace('\\\\', '\\')
    if chap_challenge_val:
        chap_challenge_val = chap_challenge_val.replace('\\\\', '\\')

    log(f"  [1/3] Extracted CHAP Params:")
    log(f"        serial: {serial_val}")
    log(f"        client_mac: {client_mac_val}")
    log(f"        client_ip: {client_ip_val}")
    log(f"        userurl: {userurl_val}")
    log(f"        login_url: {login_url_val}")
    log(f"        chap_id: {chap_id_val}")
    log(f"        chap_challenge: {chap_challenge_val}")

    if not (serial_val and client_mac_val and client_ip_val and chap_id_val and chap_challenge_val):
        log("  [1/3] ❌ Không parse được CHAP params")
        return None, None

    full_login_url = (
        f"http://v1.awingconnect.vn/login?"
        f"serial={serial_val}"
        f"&client_mac={client_mac_val}"
        f"&client_ip={client_ip_val}"
        f"&userurl={userurl_val}"
        f"&login_url={login_url_val}"
        f"&chap_id={chap_id_val}"
        f"&chap_challenge={chap_challenge_val}"
    )
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

    user_match   = re.search(r'name="username"\s+value="([^"]+)"', html_content)
    pass_match   = re.search(r'name="password"\s+value="([^"]+)"', html_content)
    action_match = re.search(r'action="([^"]+)"', html_content)

    username_val    = user_match.group(1) if user_match else CONFIG.get("default_username")
    password_val    = pass_match.group(1) if pass_match else None
    target_post_url = action_match.group(1) if action_match else "http://free.wi-mesh.vn/login"

    if not password_val:
        log("  [2/3] ❌ Không tìm thấy password trong JSON")
        return None, None, None

    log(f"  [2/3] Extracted username: {username_val}")
    log(f"  [2/3] Extracted password: {password_val}")
    log(f"  [2/3] Target POST URL: {target_post_url}")
    log(f"  [2/3] ✅ Credentials OK ({(time.time()-t2)*1000:.0f}ms)")
    return username_val, password_val, target_post_url


def perform_logout():
    log("  [0/3] GET logout URL...")
    try:
        session.mount("http://", HTTPAdapter())
        resp = session.get(CONFIG["logout_url"], timeout=3)
        log(f"  [0/3] Logout HTTP Status: {resp.status_code}")
        return True
    except Exception as e:
        log(f"  [0/3] ⚠️ Logout warning: {e}")
        return False


def perform_login_cycle():
    t_start = time.time()
    log(">>> Bắt đầu login cycle")
    
    # 0. Logout session cũ (nếu có)
    perform_logout()

    # Clear connection pool — tránh reuse TCP connection cũ đã chết sau khi WiFi drop
    session.mount("http://", HTTPAdapter())

    try:
        username, password, target_post_url = get_dynamic_credentials()
    except Exception as e:
        log(f"  ❌ Exception lấy credentials: {e}")
        return False

    if not username or not password or not target_post_url:
        log("  ❌ Hủy login — không lấy được credentials (username/password/url)")
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
    log(f"  [3/3] Target URL: {target_post_url}")
    log(f"  [3/3] Payload POST: {post_payload}")
    try:
        resp = session.post(
            target_post_url,
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

    time.sleep(0.5)
    if check_internet():
        log(f"  [3/3] ✅ Login OK & Khôi phục Internet thành công! ({(time.time()-t3)*1000:.0f}ms)")
        log(f">>> ✅ HOÀN THÀNH — tổng {duration*1000:.0f}ms")
        return True
    else:
        log("  [3/3] ❌ Gateway chưa cấp Internet sau khi POST login")
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
    connected_start_time = time.time()

    while True:
        try:
            while True:
                if check_internet():
                    if t_lost is not None:
                        # Vừa có lại mạng — tính tổng downtime
                        downtime = time.time() - t_lost
                        log(f"🌐 Có mạng lại — downtime: {downtime:.1f}s")
                        t_lost = None
                        connected_start_time = time.time()

                    elapsed = time.time() - connected_start_time
                    remaining = CONFIG["reconnect_interval"] - elapsed

                    if remaining <= 0:
                        print()  # xuống dòng sau logkv
                        log(f"⏰ Đã kết nối 14 phút ({CONFIG['reconnect_interval']}s). Thực hiện logout và login lại ngay...")
                        if perform_login_cycle():
                            connected_start_time = time.time()
                        else:
                            log("⏳ Login lại thất bại, sẽ thử lại sau 5s...")
                            time.sleep(5)
                    else:
                        mins, secs = divmod(int(remaining), 60)
                        logkv("heartbeat", f"alive (reconnect sau {mins}m{secs:02d}s)")
                        time.sleep(1)
                else:
                    if t_lost is None:
                        t_lost = time.time()  # ghi nhận thời điểm mất mạng
                    print()  # xuống dòng sau logkv
                    log("⚠️  Mất kết nối! Đang login lại...")
                    if perform_login_cycle():
                        connected_start_time = time.time()
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