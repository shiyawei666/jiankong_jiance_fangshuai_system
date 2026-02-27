import cv2
from ultralytics import YOLO
import os
import sys
import time
import requests
import base64
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from notification import NotificationManager

# 获取模型文件路径（只读）
def get_resource_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 获取可写路径（用于保存截图等）
def get_writable_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 1. 加载 YOLO11 普通检测模型
resource_path = get_resource_path()
writable_path = get_writable_path()
model_path = os.path.join(resource_path, 'yolo11l.pt')
print(f"正在加载模型: {model_path}")

model = YOLO(model_path)

# 2. 初始化通知管理器
notifier = NotificationManager()

# 加载通知配置
try:
    import config
    notification_config = {
        'feishu_webhook': getattr(config, 'feishu_webhook', None),
        'wechat_webhook': getattr(config, 'wechat_webhook', None),
        'sms_phone': getattr(config, 'sms_phone', None),
        'sms_api_key': getattr(config, 'sms_api_key', None),
        'email_to': getattr(config, 'email_to', None),
        'email_from': getattr(config, 'email_from', None),
        'email_password': getattr(config, 'email_password', None),
        'smtp_server': getattr(config, 'smtp_server', 'smtp.qq.com')
    }
    print("通知配置已加载")
except ImportError:
    print("未找到 config.py，使用默认配置（无通知）")
    notification_config = {}

# 加载截图保存路径配置
try:
    import config
    screenshot_path = getattr(config, 'screenshot_path', None)
    if screenshot_path:
        screenshot_dir = screenshot_path
        print(f"使用自定义截图路径: {screenshot_dir}")
    else:
        screenshot_dir = os.path.join(writable_path, 'screenshots')
        print(f"使用默认截图路径: {screenshot_dir}")
except ImportError:
    screenshot_dir = os.path.join(writable_path, 'screenshots')
    print(f"使用默认截图路径: {screenshot_dir}")

# 3. 尝试打开摄像头，支持多种后端
print("正在尝试打开摄像头...")

# 优先使用物理USB摄像头（索引 0），如果失败则尝试虚拟摄像头（索引 1）
camera_indices = [0, 1]  # 0=USB物理摄像头, 1=虚拟摄像头

cap = None
for camera_idx in camera_indices:
    print(f"尝试打开摄像头 {camera_idx}...")
    
    # 先尝试默认方式打开
    cap = cv2.VideoCapture(camera_idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"成功! 使用摄像头 {camera_idx}")
            break
        else:
            cap.release()
    
    # 失败了再尝试用DSHOW后端打开
    print(f"默认方式打开失败，尝试用DSHOW后端打开摄像头 {camera_idx}...")
    cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"成功! 使用摄像头 {camera_idx} (DSHOW后端)")
            break
        else:
            cap.release()
    
    cap = None
    print(f"摄像头 {camera_idx} 打开失败，尝试下一个...")

if cap is None or not cap.isOpened():
    print("\n错误: 无法打开摄像头!")
    print("请检查:")
    print("1. 如果使用 OBS 虚拟摄像头，请确保在 OBS 中已启动虚拟摄像机")
    print("2. 如果使用物理摄像头，请确保未被其他程序占用")
    print("3. 摄像头驱动是否正常")
    exit(1)

# 创建截图保存目录
if not os.path.exists(screenshot_dir):
    os.makedirs(screenshot_dir)
    print(f"截图保存目录: {screenshot_dir}")

print("\n开始人物检测，检测到人时会发送报警通知和截图...")
print("按 'q' 键退出程序\n")

last_alert_time = 0
alert_interval = 60  # 60秒内不重复报警

# 全局变量，用于视频流
latest_frame = None
latest_person_count = 0

# 创建FastAPI应用
app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket端点
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"新的WebSocket连接: {len(self.active_connections)} 个客户端")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSocket连接断开: {len(self.active_connections)} 个客户端")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"发送WebSocket消息失败: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 等待客户端消息（保持连接）
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 健康检查端点
@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "监控服务器运行中",
        "person_count": latest_person_count
    }

# 视频流推送线程
def video_stream_thread():
    global latest_frame, latest_person_count, last_alert_time
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # 使用 YOLO11 进行推理（普通检测）
        results = model(frame, verbose=False)

        person_count = 0
        current_time = 0
        screenshot_saved = False

        for r in results:
            if r.boxes is not None:
                # 获取检测框数据
                boxes = r.boxes.xywh.cpu().numpy()  # [x, y, w, h]
                classes = r.boxes.cls.cpu().numpy()  # 类别

                for i, box in enumerate(boxes):
                    x, y, w, h = box
                    cls = int(classes[i])

                    # 只检测人（person 类别通常是 0）
                    if cls == 0:
                        person_count += 1
                        status = "Person Detected"
                        color = (0, 255, 0)  # 绿色

                        # 画框和文字显示
                        cv2.rectangle(frame, (int(x - w / 2), int(y - h / 2)),
                                      (int(x + w / 2), int(y + h / 2)), color, 2)
                        cv2.putText(frame, f"{status}",
                                    (int(x - w / 2), int(y - h / 2) - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # 检测到人时保存截图并发送报警
        current_time = time.time()
        
        if person_count > 0:
            # 检查是否需要发送报警（超过报警间隔）
            if current_time - last_alert_time > alert_interval:
                # 保存截图
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                screenshot_path = os.path.join(screenshot_dir, f'detection_{timestamp}.jpg')
                cv2.imwrite(screenshot_path, frame)
                screenshot_saved = True
                
                # 构建报警消息
                message = f"【人物检测报警】\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n状态: 检测到 {person_count} 人\n\n截图已保存到: {screenshot_path}\n\n请及时查看监控画面！"
                
                # 发送报警通知
                notifier.send_notification(message, notification_config)
                
                last_alert_time = current_time
                print(f"[{time.strftime('%H:%M:%S')}] 发送报警通知: 检测到 {person_count} 人")
                print(f"[{time.strftime('%H:%M:%S')}] 截图已保存: {screenshot_path}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 未检测到人")

        # 在画面左上角显示检测到的人数
        cv2.putText(frame, f"Person Count: {person_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 显示截图状态
        if screenshot_saved:
            cv2.putText(frame, "Screenshot Saved",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            screenshot_saved = False

        # 保存最新帧
        latest_frame = frame
        latest_person_count = person_count

        # 压缩视频帧并发送到WebSocket
        try:
            # 压缩为JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ret:
                # 转换为base64
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                # 构建消息
                ws_message = {
                    "type": "video",
                    "data": {
                        "frame": frame_base64,
                        "person_count": person_count,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
                # 广播到所有WebSocket客户端
                import asyncio
                asyncio.run(manager.broadcast(ws_message))
        except Exception as e:
            print(f"WebSocket推送失败: {e}")

        # 显示画面
        cv2.imshow("YOLO11 Person Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 启动视频流线程
    video_thread = threading.Thread(target=video_stream_thread, daemon=True)
    video_thread.start()
    
    # 启动FastAPI服务器
    print("\n启动监控服务器...")
    print("服务器地址: http://0.0.0.0:8000")
    print("WebSocket地址: ws://0.0.0.0:8000/ws")
    print("健康检查: http://0.0.0.0:8000/")
    print("\n按 'q' 键退出程序\n")
    
    # 运行服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
