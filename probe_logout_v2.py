
import requests
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

urls = [
    "http://192.168.200.1/logout",
    "http://192.168.200.1/auth/logout",
    "http://192.168.200.1/goform/logout",
    "http://192.168.200.1/login?dst=logout",
    "http://192.168.200.1/login?mode=logout",
    "http://logout.net",
    "http://1.1.1.1/logout"
]

for url in urls:
    print(f"Testing {url} ...")
    try:
        resp = requests.get(url, headers=headers, timeout=2)
        print(f"GET {url} -> {resp.status_code}")
        if resp.status_code == 200:
            print(resp.text[:200])
    except Exception as e:
        print(f"GET {url} -> Error: {e}")
        
    try:
        resp = requests.post(url, headers=headers, timeout=2)
        print(f"POST {url} -> {resp.status_code}")
    except Exception as e:
        print(f"POST {url} -> Error: {e}")
