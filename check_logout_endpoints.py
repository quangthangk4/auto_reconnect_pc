
import requests

base_url = "http://192.168.200.1"
endpoints = [
    "/logout",
    "/logoff",
    "/status",
    "/goform/logout",
    "/auth/logout",
    "/login?mode=logout",
    "/login?action=logout"
]

print(f"Probing {base_url} for logout endpoints...")

for ep in endpoints:
    url = base_url + ep
    try:
        # Try GET first
        resp = requests.get(url, timeout=3, allow_redirects=True)
        print(f"GET {url} : Status {resp.status_code}, Length {len(resp.content)}")
    except Exception as e:
        print(f"GET {url} : Error {e}")
    
    try:
        # Try POST just in case
        resp = requests.post(url, timeout=3)
        print(f"POST {url} : Status {resp.status_code}, Length {len(resp.content)}")
    except Exception as e:
        print(f"POST {url} : Error {e}")
