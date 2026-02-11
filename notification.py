import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

class NotificationManager:
    def __init__(self):
        self.last_notification_time = 0
        self.notification_interval = 300  # 5分钟内不重复通知

    def should_notify(self):
        current_time = time.time()
        if current_time - self.last_notification_time > self.notification_interval:
            self.last_notification_time = current_time
            return True
        return False

    def send_feishu(self, message, webhook_url=None):
        if not webhook_url:
            print("未配置飞书 Webhook URL，跳过飞书通知")
            return False

        try:
            data = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            response = requests.post(webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print(f"飞书通知发送成功: {message}")
                    return True
                else:
                    print(f"飞书通知发送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                print(f"飞书通知发送失败: {response.text}")
                return False
        except Exception as e:
            print(f"飞书通知发送异常: {e}")
            return False

    def send_wechat(self, message, webhook_url=None):
        if not webhook_url:
            print("未配置企业微信 Webhook URL，跳过企业微信通知")
            return False

        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                print(f"企业微信通知发送成功: {message}")
                return True
            else:
                print(f"企业微信通知发送失败: {response.text}")
                return False
        except Exception as e:
            print(f"企业微信通知发送异常: {e}")
            return False

    def send_sms(self, message, phone=None, api_key=None):
        if not phone or not api_key:
            print("未配置短信参数，跳过短信通知")
            return False

        try:
            print(f"短信通知功能需要配置短信服务API")
            print(f"手机号: {phone}")
            print(f"消息内容: {message}")
            return True
        except Exception as e:
            print(f"短信通知发送异常: {e}")
            return False

    def send_email(self, message, to_email=None, from_email=None, smtp_password=None, smtp_server="smtp.qq.com"):
        if not to_email or not from_email or not smtp_password:
            print("未配置邮件参数，跳过邮件通知")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = "跌倒检测报警"

            msg.attach(MIMEText(message, 'plain', 'utf-8'))

            server = smtplib.SMTP(smtp_server, 587)
            server.starttls()
            server.login(from_email, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()

            print(f"邮件通知发送成功: {message}")
            return True
        except Exception as e:
            print(f"邮件通知发送异常: {e}")
            return False

    def send_notification(self, message, config=None):
        if not self.should_notify():
            print("通知间隔未到，跳过本次通知")
            return

        if config is None:
            config = {}

        print(f"\n{'='*50}")
        print(f"🚨 跌倒报警通知")
        print(f"{'='*50}")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"内容: {message}")
        print(f"{'='*50}\n")

        # 发送飞书通知（优先）
        if config.get('feishu_webhook'):
            self.send_feishu(message, config['feishu_webhook'])

        # 发送企业微信通知
        if config.get('wechat_webhook'):
            self.send_wechat(message, config['wechat_webhook'])

        # 发送短信通知
        if config.get('sms_phone') and config.get('sms_api_key'):
            self.send_sms(message, config['sms_phone'], config['sms_api_key'])

        # 发送邮件通知
        if config.get('email_to') and config.get('email_from') and config.get('email_password'):
            self.send_email(
                message,
                config['email_to'],
                config['email_from'],
                config['email_password'],
                config.get('smtp_server', 'smtp.qq.com')
            )
