import os
import time
import socket
import requests
import subprocess
import json

# ==========================================
# 🔧 个人配置区 (请根据实际情况修改)
# ==========================================
STUDENT_ID = "你的学号"
PASSWORD   = "你的密码"
# MAC地址通常在 ipconfig /all 里查看，格式如: A0B1C2D3E4F5
MAC_ADDR   = "你的网卡MAC地址"

# Windows 下有线网卡的名称，通常叫 "以太网" 或 "Ethernet"
ETHERNET_NAME = "以太网"

# 校园网登录网关地址 (培正学院默认)
GATEWAY   = "10.20.3.1"
LOGIN_URL = f"http://{GATEWAY}:801/eportal/"

# 手机/平板 USB 共享适配器的硬件关键字
PHONE_KEYWORDS = ["Remote NDIS", "USB Ethernet", "Apple Mobile Device", "SAMSUNG Mobile USB"]
# ==========================================

def get_adapters():
    """使用 PowerShell 获取所有网卡的硬件描述和状态"""
    cmd = 'powershell "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status | ConvertTo-Json"'
    try:
        res = subprocess.check_output(cmd, shell=True).decode('gbk')
        data = json.loads(res)
        return data if isinstance(data, list) else [data]
    except:
        return []

def is_phone_active():
    """检测手机 USB 热点是否处于连接状态"""
    adapters = get_adapters()
    for adapter in adapters:
        desc = adapter.get("InterfaceDescription", "")
        status = adapter.get("Status", "")
        # 如果硬件描述匹配关键字且状态为 Up (已连接)
        if any(key in desc for key in PHONE_KEYWORDS) and status == "Up":
            return True
    return False

def set_ethernet(enable=True):
    """开启或禁用有线网口 (需管理员权限)"""
    action = "enable" if enable else "disable"
    os.system(f'netsh interface set interface "{ETHERNET_NAME}" admin={action}')

def check_internet():
    """
    通过 HTTPS 访问百度检测外网。
    1. HTTPS 握手失败通常意味着被校园网劫持。
    2. 检查返回内容中是否包含 'baidu'，防止网关伪造 200 页面。
    """
    try:
        r = requests.get("https://www.baidu.com", timeout=3)
        if r.status_code == 200 and "baidu" in r.text.lower():
            return True
        return False
    except:
        return False

def do_login():
    """执行校园网敲门登录逻辑"""
    try:
        # 动态获取当前有线网口的内网 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((GATEWAY, 80))
        current_ip = s.getsockname()[0]
        s.close()
        
        # 构造培正 eportal 系统的登录参数
        params = {
            "c": "Portal",
            "a": "login",
            "callback": "dr1004",
            "login_method": "1",
            "user_account": f",0,{STUDENT_ID}",
            "user_password": PASSWORD,
            "wlan_user_ip": current_ip,
            "wlan_user_mac": MAC_ADDR,
            "wlan_ac_ip": "10.20.3.254", # AC 控制器 IP
            "wlan_ac_name": "H3C8808",   # 核心交换机型号
            "jsVersion": "3.3.3",
            "v": str(int(time.time()) % 10000) # 随机版本号
        }
        
        res = requests.get(LOGIN_URL, params=params, timeout=5)
        if '"result":"1"' in res.text or '"ret_code":2' in res.text:
            print(f"\n[{time.strftime('%H:%M:%S')}] ✅ 自动重连成功 (或已在线)")
        else:
            print(f"\n[{time.strftime('%H:%M:%S')}] ⚠️ 响应异常: {res.text[:50]}")
    except Exception as e:
        print(f"\n[!] 登录尝试失败: {e}")

if __name__ == "__main__":
    print("🚀 校园网守护进程已启动...")
    print(f"当前策略：手机热点优先 | 3秒心跳巡逻 | HTTPS 劫持识破")
    
    eth_enabled = True 

    while True:
        # 阶段 1: 物理分流检测
        if is_phone_active():
            if eth_enabled:
                print("\n🚨 检测到手机热点，正在封锁有线网口，确保流量不侧漏...")
                set_ethernet(False)
                eth_enabled = False
            print("📱", end="", flush=True) # 手机模式心跳
            time.sleep(10)
            continue
        
        # 阶段 2: 恢复有线网
        if not eth_enabled:
            print("\n🔌 手机热点已断开，正在恢复有线网口...")
            set_ethernet(True)
            eth_enabled = True
            time.sleep(5) # 等待硬件初始化

        # 阶段 3: 校园网巡逻
        if check_internet():
            print(".", end="", flush=True) # 正常在线心跳
            time.sleep(3)
        else:
            print(f"\n[{time.strftime('%H:%M:%S')}] 💔 信号丢失或被劫持，正在敲门...")
            do_login()
            time.sleep(2)
