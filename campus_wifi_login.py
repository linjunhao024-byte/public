import os
import time
import socket
import requests
import subprocess
import json
import random
import sys

# ==========================================
# 🔧 核心配置区 (开源/分享时请修改此处)
# ==========================================
STUDENT_ID = "000000000000"# 学号 (必填，认证账号的一部分)
PASSWORD   = "000000" # 密码 (必填，认证账号的一部分，建议设置复杂密码以防泄露后被人恶意使用)

ETHERNET_NAME = "以太网"          # 有线网卡名称
GATEWAY       = "10.20.3.1"      # 校园网认证网关
AC_IP         = "10.20.3.254"    # 浏览器跳转链接中的 wlanacip (培正必备)
LOGIN_URL     = f"http://{GATEWAY}:801/eportal/"

# 手机/平板 USB 共享适配器识别关键字
PHONE_KEYWORDS = ["Remote NDIS", "USB Ethernet", "Apple Mobile Device", "SAMSUNG Mobile USB"]

# --- 潮汐算法与状态参数 ---
BASE_RETRY_INTERVAL   = 2    # 初始尝试间隔 (秒)
MAX_RETRY_INTERVAL    = 300  # 最大休眠上限 (5分钟)
NORMAL_CHECK_INTERVAL = 5    # 联网状态下的巡逻频率 (秒)
MUTEX_PORT            = 65432 # 单例锁端口 (防止脚本多开)

# ==========================================
# 🛠️ 内部功能模块
# ==========================================

def enforce_single_instance():
    """优化1：单例锁，防止小白双击多次导致后台神仙打架"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', MUTEX_PORT))
        return s  # 返回并保持变量存活，直到脚本结束
    except socket.error:
        print("检测到另一个守护进程已在运行，当前实例自动退出。")
        sys.exit()

def write_log(message):
    """静默日志：仅记录关键状态切换"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    try:
        with open("guardian_activity.log", "a", encoding="utf-8") as f:
            f.write(log_line)
    except:
        pass

def get_adapters():
    cmd = 'powershell "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status | ConvertTo-Json"'
    try:
        res = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW).decode('gbk')
        data = json.loads(res)
        return data if isinstance(data, list) else [data]
    except:
        return []

def is_phone_active():
    adapters = get_adapters()
    for adapter in adapters:
        desc = adapter.get("InterfaceDescription", "")
        status = adapter.get("Status", "")
        if any(key in desc for key in PHONE_KEYWORDS) and status == "Up":
            return True
    return False

def set_ethernet(enable=True):
    action = "enable" if enable else "disable"
    # 添加 CREATE_NO_WINDOW 防止后台运行时突然弹出黑框闪烁
    subprocess.call(f'netsh interface set interface "{ETHERNET_NAME}" admin={action}', 
                    shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    write_log(f"硬件指令：有线网卡已执行 {action}")

def is_at_school():
    """地理感知：探测是否在培正内网物理环境中"""
    try:
        with socket.create_connection((GATEWAY, 801), timeout=1):
            return True
    except:
        return False

def check_internet():
    """HTTPS 深度探测"""
    try:
        r = requests.get("https://www.baidu.com", timeout=3)
        return r.status_code == 200 and "baidu" in r.text.lower()
    except:
        return False

def do_login():
    """执行 Portal 认证协议"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((GATEWAY, 801))
        current_ip = s.getsockname()[0]
        s.close()

        params = {
            "c": "Portal", "a": "login", "callback": "dr1004", 
            "login_method": "1", "user_account": f",0,{STUDENT_ID}", 
            "user_password": PASSWORD, "wlan_user_ip": current_ip,
            "wlan_user_ipv6": "", "wlan_vlan_id": "0",
            "wlan_user_mac": "000000000000",
            "wlan_ac_ip": AC_IP,  # <--- 使用顶部配置的变量
            "wlan_ac_name": "", "jsVersion": "3.3.3"
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(LOGIN_URL, params=params, headers=headers, timeout=5)
        
        # 兼容培正网关 "1" (已在线/成功) 和 "0"
        if '"result":"1"' in r.text or '"result":"0"' in r.text:
            write_log("网关反馈：认证通过 (或已在线)。")
        else:
            write_log(f"网关反馈异样: {r.text[:80]}")
    except Exception as e:
        write_log(f"认证执行异常: {str(e)}")

# ==========================================
# 🚀 守护进程主逻辑
# ==========================================

if __name__ == "__main__":
    _lock = enforce_single_instance() # 开启单例防多开保护
    
    write_log("=== CampusNet Guardian V6.0 启动成功 (作者: 林师傅) ===")
    eth_enabled = True
    current_interval = BASE_RETRY_INTERVAL

    while True:
        try:
            # 1. 物理优先级检测
            if is_phone_active():
                if eth_enabled:
                    write_log("检测到手机热点，正在物理封锁有线网口防侧漏...")
                    set_ethernet(False)
                    eth_enabled = False
                time.sleep(10)
                continue

            # 2. 恢复模式
            if not eth_enabled:
                write_log("热点已断开，唤醒有线网口...")
                set_ethernet(True)
                eth_enabled = True
                time.sleep(5)

            # 3. 潮汐式重连监控与地理感知
            if check_internet():
                # 【网络畅通】
                if current_interval != BASE_RETRY_INTERVAL:
                    write_log("链路连通，重置探测频率。")
                    current_interval = BASE_RETRY_INTERVAL
                
                print(".", end="", flush=True) # 仅屏幕打点，不写日志
                time.sleep(NORMAL_CHECK_INTERVAL)
            else:
                # 【网络中断】
                if is_at_school():
                    write_log("检测到断网且处于校园网环境，发起认证冲锋...")
                    do_login()

                    if current_interval >= MAX_RETRY_INTERVAL:
                        write_log(f"已达休眠上限 ({MAX_RETRY_INTERVAL}s)，重置为快速冲锋模式。")
                        current_interval = BASE_RETRY_INTERVAL
                        actual_sleep = current_interval
                    else:
                        jitter = random.uniform(-0.5, 0.5)
                        actual_sleep = current_interval + jitter
                        write_log(f"休眠 {actual_sleep:.2f}s 后翻倍重试...")
                        current_interval = min(current_interval * 2, MAX_RETRY_INTERVAL + 1)
                    
                    time.sleep(max(1, actual_sleep))
                else:
                    # 【异地待机】(如在外使用其他Wi-Fi)
                    print("x", end="", flush=True) # 仅屏幕打叉，不写日志，不发包
                    time.sleep(30)
                    
        except Exception as e:
            # 优化3：全局异常熔断，防止系统级错误导致死循环吃满 CPU
            write_log(f"致命运行错误: {str(e)}。进入 30 秒熔断休眠...")
            time.sleep(30)