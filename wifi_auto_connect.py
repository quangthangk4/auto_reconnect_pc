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
from urllib.parse import urlencode
from datetime import datetime

# ============ CẤU HÌNH ============
CONFIG = {
    "username":       "awing15-15",
    "gateway_url":    "http://192.168.200.1/login",
    "api_verify_url": "http://v1.awingconnect.vn/Home/VerifyUrl",
    "check_url":      "http://www.google.com/generate_204",
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

def get_dynamic_password():
    # Step 1: Lấy CHAP params từ gateway
    # Dùng timeout ngắn (1.5s connect, 2s read) + retry nhanh để tránh chờ TCP retransmit (~3-5s)
    log("  [1/3] GET gateway login page...")
    t1 = time.time()
    html_body = None
    for attempt in range(6):
        try:
            session.mount("http://", HTTPAdapter())  # fresh TCP mỗi lần thử
            resp = session.get(CONFIG["gateway_url"], allow_redirects=False, timeout=(1.5, 2))
            html_body = resp.content.decode("utf-8", errors="ignore")
            break
        except Exception:
            if attempt < 5:
                time.sleep(0.3)

    if html_body is None:
        log(f"  [1/3] ❌ Gateway không phản hồi sau 6 lần thử ({(time.time()-t1)*1000:.0f}ms)")
        return None

    serial         = re.search(r'id="serial" value="([^"]*)"', html_body)
    client_mac     = re.search(r'id="client_mac" value="([^"]*)"', html_body)
    client_ip      = re.search(r'id="client_ip" value="([^"]*)"', html_body)
    login_url      = re.search(r'id="login_url" value="([^"]*)"', html_body)
    chap_id        = re.search(r'id="chap-id" value="([^"]*)"', html_body)
    chap_challenge = re.search(r'id="chap-challenge" value="([^"]*)"', html_body)

    if not (serial and client_mac and client_ip and chap_id and chap_challenge):
        log("  [1/3] ❌ Không parse được CHAP params")
        return None

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
    log(f"  [1/3] ✅ CHAP params OK ({(time.time()-t1)*1000:.0f}ms)")

    # Step 2: Lấy dynamic password từ VerifyUrl
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

    try:
        data = resp_api.json()
    except Exception:
        log(f"  [2/3] ❌ Response không phải JSON: {resp_api.text[:100]}")
        return None

    html_content = data.get("captiveContext", {}).get("contentAuthenForm", "")
    pass_match = re.search(r'name="password"\s+value="([^"]+)"', html_content)

    if not pass_match:
        log("  [2/3] ❌ Không tìm thấy password trong JSON")
        return None

    log(f"  [2/3] ✅ Password OK ({(time.time()-t2)*1000:.0f}ms)")
    return pass_match.group(1)


def perform_login_cycle():
    t_start = time.time()
    log(">>> Bắt đầu login cycle")
    # Clear connection pool — tránh reuse TCP connection cũ đã chết sau khi WiFi drop
    session.mount("http://", HTTPAdapter())

    try:
        password = get_dynamic_password()
    except Exception as e:
        log(f"  ❌ Exception lấy password: {e}")
        return False

    if not password:
        log("  ❌ Hủy login — không lấy được password")
        return False

    # Step 3: POST login về gateway
    log("  [3/3] POST login gateway...")
    t3 = time.time()
    try:
        resp = session.post(
            CONFIG["gateway_url"],
            data={
                "username": CONFIG["username"],
                "password": password,
                "dst":      "http://v1.awingconnect.vn/Success",
                "popup":    "false",
            },
            timeout=5,
        )
    except Exception as e:
        log(f"  [3/3] ❌ Exception: {e}")
        return False

    duration = time.time() - t_start
    if resp.status_code < 400:
        log(f"  [3/3] ✅ Login OK ({(time.time()-t3)*1000:.0f}ms)")
        log(f">>> ✅ HOÀN THÀNH — tổng {duration*1000:.0f}ms")
        return True
    else:
        log(f"  [3/3] ❌ Gateway trả HTTP {resp.status_code}")
        return False


def check_internet():
    try:
        r = requests.get(CONFIG["check_url"], timeout=3)
        return r.status_code == 204
    except:
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
