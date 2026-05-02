import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Kiểm tra trang Success trước - thường có nút logout
print("=== Kiểm tra trang Success ===")
try:
    r = requests.get("http://v1.awingconnect.vn/Success", headers=headers, timeout=5)
    print(f"GET /Success -> {r.status_code}")
    # Tìm link logout trong HTML
    import re
    links = re.findall(r'href=["\']([^"\']*logout[^"\']*)["\']', r.text, re.IGNORECASE)
    actions = re.findall(r'action=["\']([^"\']*logout[^"\']*)["\']', r.text, re.IGNORECASE)
    if links:
        print(f"  >> Tìm thấy logout links: {links}")
    if actions:
        print(f"  >> Tìm thấy form actions: {actions}")
    if not links and not actions:
        print(f"  >> Không có link logout rõ ràng trong HTML")
        print(f"  >> Đoạn HTML đầu: {r.text[:500]}")
except Exception as e:
    print(f"  >> Error: {e}")

print()
print("=== Probe cloud logout endpoints ===")
endpoints = [
    "http://v1.awingconnect.vn/logout",
    "http://v1.awingconnect.vn/logoff",
    "http://v1.awingconnect.vn/Home/Logout",
    "http://v1.awingconnect.vn/Account/Logout",
    "http://v1.awingconnect.vn/Login/Logout",
    "http://authen.awingconnect.vn/logout",
    "http://authen.awingconnect.vn/logoff",
]

for url in endpoints:
    try:
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
        print(f"GET {url} -> {r.status_code} | Location: {r.headers.get('Location', '-')}")
    except Exception as e:
        print(f"GET {url} -> Error: {e}")
