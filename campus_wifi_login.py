import os
import time
import requests

# --- 配置区 ---
# 填写你刚才抓到的登录 URL
LOGIN_URL = "这里填入你抓到的请求URL"
# 填写你抓到的 Data 负载（通常是字典格式）
LOGIN_DATA = {
    "username": "你的学号",
    "password": "你的密码",
    # ... 其他从 cURL 里看到的参数
}
# 检测目标，建议用国内秒开的地址
CHECK_URL = "http://www.baidu.com"
INTERVAL = 60  # 每 60 秒检查一次

def check_internet():
    try:
        # 设置 5 秒超时，防止被校园网劫持页面卡死
        response = requests.get(CHECK_URL, timeout=5)
        if response.status_code == 200 and "baidu" in response.text:
            return True
    except:
        pass
    return False

def login():
    print(f"[{time.strftime('%H:%M:%S')}] 检测到断网，正在尝试登录...")
    try:
        res = requests.post(LOGIN_URL, data=LOGIN_DATA, timeout=10)
        print(f"响应结果: {res.text[:100]}")
    except Exception as e:
        print(f"登录异常: {e}")

if __name__ == "__main__":
    print("🚀 校园网自动守护脚本已启动...")
    while True:
        if not check_internet():
            login()
        else:
            # 这里的打印可以删掉，保持静默运行
            print(".", end="", flush=True) 
        time.sleep(INTERVAL)