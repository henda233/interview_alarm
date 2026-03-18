import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import json
import os
import time
from datetime import datetime

# 硬编码目标 URL
TARGET_URL = "https://cs.gzu.edu.cn/16270/list.htm"
CONFIG_FILE = "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "check_time": 15,          # 爬取间隔（分钟）
    "live_time": 180,          # 心跳间隔（分钟）
    "smtp_server": "smtp.163.com",
    "smtp_port": 465,
    "sender_email": "",  # 用户需修改
    "sender_auth_code": "",  # 用户需修改
    "receiver_email": "",
    "base_date": "2026-03-13"  # 基准日期
}

def load_config():
    """
    读取配置文件，如果不存在自动创建并采用默认值。
    返回配置字典。
    """
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()
    else:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 确保配置完整性，若有缺失则补充默认值
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception:
            # 如果配置文件损坏，重置为默认
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            return DEFAULT_CONFIG.copy()

def save_config(config):
    """
    保存配置字典到 JSON 文件。
    """
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def fetch_notice(config):
    """
    输入配置字典。
    伪造请求头，请求并获取目标网页 HTML，解析获取第一条通告的发布日期和标题。
    根据配置字典的基准日期判断第一条是否为最新通告，并将其视为复试通告。
    如果是复试通告，将配置字典中的基准日期更新为最新日期，保存配置，
    返回 (config, 标题，发布日期)，否则返回 None。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding # 自动处理编码
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 选择第一条通告
        # 选择器：ul.wp_article_list 下的 li.list_item.i1
        first_item = soup.select_one('ul.wp_article_list li.list_item.i1')
        
        if not first_item:
            return None
            
        title_tag = first_item.select_one('span.Article_Title a')
        date_tag = first_item.select_one('span.Article_PublishDate')
        
        if not title_tag or not date_tag:
            return None
            
        title = title_tag.get('title', '').strip()
        publish_date = date_tag.get_text(strip=True)
        
        # 判断是否为新通告
        base_date = config.get("base_date", "")
        
        if publish_date != base_date:
            # 发现新通告
            config["base_date"] = publish_date
            save_config(config)
            return (config, title, publish_date)
        else:
            return None
            
    except Exception as e:
        # 网络异常等情况，直接结束进程
        print(f"Critical Error: 爬取失败，程序终止。错误信息：{e}")
        import sys
        sys.exit(1)

def send_email(config, subject, content):
    """
    输入配置字典，邮件标题和邮件正文。
    登录邮箱，向目标用户邮箱地址发送相应的标题和正文。
    """
    smtp_server = config["smtp_server"]
    smtp_port = config["smtp_port"]
    sender = config["sender_email"]
    auth_code = config["sender_auth_code"]
    receiver = config["receiver_email"]
    
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender, auth_code)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
    except Exception:
        # 发送失败不中断程序
        pass

def is_work_time():
    """
    判断当前时间是否在早上 8 点到晚上 10 点，如果是则返回真，否则为假。
    """
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 22:
        return True
    return False

def main_loop(config):
    """
    接收配置字典。
    这是主程序，主循环。
    实现定时爬取判断、发送心跳包和非工作时间暂停运行。
    """
    # 记录上次爬取和心跳的时间戳（初始化为 0 以便启动后立即执行一次检查）
    last_check_time = 0
    last_heartbeat_time = 0
    
    # 将分钟转换为秒
    check_interval = config["check_time"] * 60
    heartbeat_interval = config["live_time"] * 60
    
    while True:
        # 获取当前时间用于日志
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 判断是否为工作时间
        if not is_work_time():
            # 非工作时间，暂停运行，睡眠 1 分钟后再次检查
            print(f"[{current_time_str}] 非工作时间，暂停运行。")
            time.sleep(60)
            continue
            
        now = time.time()
        
        # 2. 定时爬取判断
        if now - last_check_time >= check_interval:
            print(f"[{current_time_str}] 开始检查通告...")
            result = fetch_notice(config)
            if result:
                # 更新 config 引用（虽然字典是 mutable，但为了逻辑清晰）
                config = result[0]
                title = result[1]
                # 发送复试通告邮件
                send_email(config, "[IA] 疑似复试通告发布！", title)
                print(f"[{current_time_str}] 发现新通告！标题：{title}")
            else:
                print(f"[{current_time_str}] 未发现新通告。")
        
            # 无论是否发现新通告，都更新上次爬取时间
            last_check_time = now
            
        # 3. 发送心跳包
        if now - last_heartbeat_time >= heartbeat_interval:
            send_email(config, "[IA] 心跳反馈", "这是心跳包。")
            print(f"[{current_time_str}] 已发送心跳包。")
            last_heartbeat_time = now
            
        # 4. 短暂睡眠，避免 CPU 占用过高，同时保证分钟级精度
        # 睡眠 1 分钟足够满足 15 分钟和 3 小时的精度要求
        time.sleep(60)

def main():
    """
    首先运行配置文件函数获取配置字典，然后进入主循环函数。
    """
    config = load_config()
    main_loop(config)

def test1():
    config = load_config()
    fetch_notice(config)

def test2():
    config = load_config()
    send_email(config,"[IA] 这是测试邮件","这是测试邮件")

if __name__ == "__main__":
    main()