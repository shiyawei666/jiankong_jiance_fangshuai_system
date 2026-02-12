# 软件系统方案
```
硬件：
1. 旧手机，带有UC浏览器,访问地址【vdo.ninja】
2. 旧电脑，安装上obs-studio 【https://github.com/obsproject/obs-studio】
3. wifi，要求手机与电脑连接到同一个wifi下
软件：自己实现的摔倒检测算法


更低成本的方案
硬件：旧电脑需要有摄像头，安装上obs-studio 【https://github.com/obsproject/obs-studio】
操作步骤
1. 浏览器上先访问【vdo.ninja】
2. 打开obs studio，然后添加上浏览器生成的监控源：例如：https://vdo.ninja/?view=bSdk4Lu
3. 启动虚拟机摄像头
4. 运行main.py程序
```

## 跌倒报警通知功能

系统支持多种通知方式，当检测到人员跌倒时会自动发送报警通知。

### 支持的通知方式

1. **飞书机器人通知（推荐）** - 发送到飞书群聊
2. **企业微信机器人通知** - 发送到企业微信群聊
3. **短信通知** - 发送到手机短信
4. **邮件通知** - 发送到邮箱

### 配置通知功能

编辑 `config.py` 文件，填写相应的配置信息：

```python
# 飞书机器人 Webhook URL（推荐）
feishu_webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_URL"

# 企业微信机器人 Webhook URL
wechat_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 短信通知（需要申请短信服务）
sms_phone = "13800138000"
sms_api_key = "your_sms_api_key"

# 邮件通知（以QQ邮箱为例）
email_to = "admin@example.com"
email_from = "your@qq.com"
email_password = "your_qq_mail_auth_code"  # QQ邮箱授权码，不是QQ密码
smtp_server = 'smtp.qq.com'
```

### 飞书机器人配置步骤

1. 在飞书群聊中，点击右上角 "..."
2. 选择 "群设置" -> "群机器人" -> "添加机器人"
3. 选择 "自定义机器人"
4. 设置机器人名称，点击 "添加"
5. 复制 Webhook 地址，填入 `config.py` 的 `feishu_webhook` 字段
6. 完成！现在报警信息会发送到飞书群聊

### 企业微信机器人配置步骤

1. 在企业微信群聊中，点击右上角 "..."
2. 选择 "群机器人" -> "添加机器人"
3. 设置机器人名称，点击 "添加"
4. 复制 Webhook 地址，填入 `config.py` 的 `wechat_webhook` 字段

### 邮件通知配置步骤（QQ邮箱）

1. 登录 QQ 邮箱网页版
2. 点击 "设置" -> "账户"
3. 找到 "POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启 "POP3/SMTP服务"
5. 生成授权码（不是QQ密码）
6. 将授权码填入 `config.py` 的 `email_password` 字段

### 通知机制

- 默认 5 分钟内不会重复发送通知，避免频繁打扰
- 通知内容包含：报警时间、报警状态、提示信息
- 可在 `config.py` 中修改 `notification_interval` 调整通知间隔
- 系统会优先发送飞书通知，如果配置了多种通知方式，会依次尝试发送

## 打包指南

### 安装依赖
```bash
pip install -r requirement.txt
pip install pyinstaller
```

### 重新打包命令
当代码变更后，执行以下命令重新生成可执行文件：

```bash
# 清理旧的打包文件
rmdir /s /q "dist" 2>nul
rmdir /s /q "build" 2>nul

# 重新打包（使用 spec 文件）
pyinstaller fall_detection.spec
```

### 或者直接使用命令行打包
```bash
# 清理旧的打包文件
rmdir /s /q "dist" 2>nul
rmdir /s /q "build" 2>nul

# 直接打包 main2.py
pyinstaller --onefile --add-data "yolo11l.pt;." --add-data "notification.py;." --add-data "config.py;." --name fall_detection main2.py
```

### 打包结果
生成的可执行文件位于：
- **单文件版本**：`dist/fall_detection.exe`

### 运行说明
1. 在 OBS Studio 中启动虚拟摄像机
2. 双击 `fall_detection.exe` 运行
3. 程序会自动加载模型并开始检测
4. 按 `q` 键退出程序

### 截图保存路径配置
在 `config.py` 中可以配置截图保存路径，避免占用C盘空间：

```python
# 保存到D盘（推荐）
screenshot_path = "D:\\screenshots"

# 或保存到其他盘符
# screenshot_path = "E:\\monitor\\screenshots"

# 或使用默认路径（exe所在目录）
# screenshot_path = None
```

### 注意事项
- 打包过程会包含 `yolo11l.pt` 模型文件，无需单独下载
- 首次运行可能需要较长时间加载模型
- 如果运行卡顿，可以调整 OBS 的输出分辨率
- 如需使用通知功能，请确保 `config.py` 文件与可执行文件在同一目录
- 截图默认保存到D盘，可在 `config.py` 中修改 `screenshot_path` 配置
- 打包后首次运行会自动创建截图保存目录
