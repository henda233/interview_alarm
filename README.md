# 复试通告自动抓取程序：复试警报 Interview Alarm

自用程序。

定时爬取目标院校通告网页，判断是否发布复试通告，并即时以电子邮件的方式告知用户。

## 配置文件说明

```json
{
    "check_time": 15,   // 爬取间隔（分钟）
    "live_time": 180,   // 心跳间隔（分钟）
    "smtp_server": "smtp.163.com",  // SMTP服务器
    "smtp_port": 465,   // SMTP端口
    "sender_email": "", // 程序的邮箱地址
    "sender_auth_code": "", // 校验码
    "receiver_email": "",   // 用户消息接收邮箱地址
    "base_date": "2026-03-13"   // 基准日期
}

```