#!/usr/bin/env python3
"""
Test DHCP renewal approach vs retry approach
So sánh thời gian step [1/3] giữa 2 cách xử lý TCP retransmit delay
Chạy với quyền Administrator để ipconfig /renew hoạt động
"""

import requests
from requests.adapters import HTTPAdapter
import subprocess
import time
import re
import sys
from urllib.parse import urlencode
from datetime import datetime

CONFIG = {
    "username":       "awing15-15",
    "gateway_url":    "http://192.168.200.1/login",
    "api_verify_url": "http://v1.awingconnect.vn/Home/VerifyUrl",
    "check_url":      "http://www.google.com/generate_204",
    "wifi_adapter":   "Wi-Fi",  # tên adapter, xem trong ipconfig
}

session = requests.Session()
session.headers.update({
    "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection":       "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Accept":           "*/*",
})

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}")

def logkv(key, value):
    sys.stdout.write(f"\r[{ts()}] {key}: {value}        ")
    sys.stdout.flush()

# ── DHCP renewal ──────────────────────────────────────────────────────────────

def renew_dhcp():
    """Gửi DHCP renew để gateway reset state client về unauthenticated ngay lập tức."""
    adapter = CONFIG["wifi_adapter"]
    log(f"  [DHCP] ipconfig /renew \"{adapter}\" ...")
    t = time.time()
    try:
        result = subprocess.run(
            ["ipconfig", "/renew", adapter],
            capture_output=True, text=True, timeout=15
        )
        elapsed = (time.time() - t) * 1000
        if result.returncode == 0:
            log(f"  [DHCP] ✅ Renew xong ({elapsed:.0f}ms)")
            return True
        else:
            log(f"  [DHCP] ❌ Lỗi ({elapsed:.0f}ms): {result.stderr.strip()[:100]}")
            log(f"  [DHCP] ⚠️  Có thể cần chạy script với quyền Administrator")
            return False
    except subprocess.TimeoutExpired:
        log("  [DHCP] ❌ Timeout sau 15s")
        return False
    except Exception as e:
        log(f"  [DHCP] ❌ Exception: {e}")
        return False

# ── Login steps ───────────────────────────────────────────────────────────────


def get_dynamic_password_with_dhcp():
    """Step 1: DHCP renew trước, rồi retry loop ngắn."""
    log("  [1/3] DHCP renew...")
    renew_dhcp()

    log("  [1/3] GET gateway login page...")
    t1 = time.time()
    html_body = None
    for attempt in range(6):
        session.mount("http://", HTTPAdapter())
        try:
            resp = session.get(CONFIG["gateway_url"], allow_redirects=False, timeout=(1.5, 2))
            html_body = resp.content.decode("utf-8", errors="ignore")
            if attempt > 0:
                log(f"  [1/3] Thành công ở lần thử {attempt + 1}")
            break
        except Exception:
            if attempt < 5:
                time.sleep(0.3)

    if not html_body:
        log(f"  [1/3] ❌ Gateway không phản hồi sau 6 lần thử ({(time.time()-t1)*1000:.0f}ms)")
        return None
    log(f"  [1/3] ✅ CHAP params OK ({(time.time()-t1)*1000:.0f}ms)")
    return _parse_and_get_password(html_body)

def get_dynamic_password_with_retry():
    """Step 1: Retry nhanh với timeout ngắn (bản gốc)."""
    log("  [1/3] GET gateway login page (retry loop)...")
    t1 = time.time()
    html_body = None
    for attempt in range(6):
        session.mount("http://", HTTPAdapter())
        try:
            resp = session.get(CONFIG["gateway_url"], allow_redirects=False, timeout=(1.5, 2))
            html_body = resp.content.decode("utf-8", errors="ignore")
            if attempt > 0:
                log(f"  [1/3] Thành công ở lần thử {attempt + 1}")
            break
        except Exception:
            if attempt < 5:
                time.sleep(0.3)

    if not html_body:
        log(f"  [1/3] ❌ Gateway không phản hồi sau 6 lần thử ({(time.time()-t1)*1000:.0f}ms)")
        return None
    log(f"  [1/3] ✅ CHAP params OK ({(time.time()-t1)*1000:.0f}ms)")
    return _parse_and_get_password(html_body)

def _parse_and_get_password(html_body):
    """Dùng chung: parse CHAP → VerifyUrl → return password."""
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

    log("  [2/3] POST VerifyUrl...")
    t2 = time.time()
    try:
        resp_api = session.post(
            CONFIG["api_verify_url"],
            headers={"Host": "v1.awingconnect.vn", "Referer": full_login_url, "Content-Type": "application/json"},
            json={}, timeout=10,
        )
        data = resp_api.json()
    except Exception as e:
        log(f"  [2/3] ❌ {e}")
        return None

    html_content = data.get("captiveContext", {}).get("contentAuthenForm", "")
    pass_match = re.search(r'name="password"\s+value="([^"]+)"', html_content)
    if not pass_match:
        log("  [2/3] ❌ Không tìm thấy password")
        return None
    log(f"  [2/3] ✅ Password OK ({(time.time()-t2)*1000:.0f}ms)")
    return pass_match.group(1)

def do_login(password):
    log("  [3/3] POST login gateway...")
    t3 = time.time()
    try:
        resp = session.post(
            CONFIG["gateway_url"],
            data={"username": CONFIG["username"], "password": password,
                  "dst": "http://v1.awingconnect.vn/Success", "popup": "false"},
            timeout=5,
        )
        elapsed = (time.time() - t3) * 1000
        if resp.status_code < 400:
            log(f"  [3/3] ✅ Login OK ({elapsed:.0f}ms)")
            return True
        else:
            log(f"  [3/3] ❌ HTTP {resp.status_code}")
            return False
    except Exception as e:
        log(f"  [3/3] ❌ {e}")
        return False

# ── Main loop ─────────────────────────────────────────────────────────────────

def perform_login_cycle(use_dhcp: bool):
    t_start = time.time()
    method = "DHCP renew" if use_dhcp else "Retry loop"
    log(f">>> Login cycle [{method}]")
    session.mount("http://", HTTPAdapter())

    password = get_dynamic_password_with_dhcp() if use_dhcp else get_dynamic_password_with_retry()
    if not password:
        log("  ❌ Không lấy được password")
        return False

    if not do_login(password):
        return False

    log(f">>> ✅ HOÀN THÀNH — tổng {(time.time()-t_start)*1000:.0f}ms")
    return True

def check_internet():
    try:
        r = requests.get(CONFIG["check_url"], timeout=3)
        return r.status_code == 204
    except:
        return False

def main():
    # Đổi USE_DHCP = True để test DHCP renew, False để test retry loop
    USE_DHCP = True

    log(f"=== TEST: {'DHCP renew' if USE_DHCP else 'Retry loop'} ===")
    log(f"=== Chờ mất mạng để đo downtime... ===")

    t_lost = None
    while True:
        try:
            while True:
                if check_internet():
                    if t_lost is not None:
                        downtime = time.time() - t_lost
                        log(f"🌐 Có mạng lại — downtime: {downtime:.1f}s")
                        t_lost = None
                    logkv("heartbeat", "alive")
                    time.sleep(1)
                else:
                    if t_lost is None:
                        t_lost = time.time()
                    print()
                    log("⚠️  Mất kết nối! Đang login lại...")
                    if perform_login_cycle(USE_DHCP):
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
