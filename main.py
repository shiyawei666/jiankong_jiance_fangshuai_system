import cv2
from ultralytics import YOLO
import os
import sys
from notification import NotificationManager

# 获取应用程序路径
def get_app_path():
    # PyInstaller 打包后会设置 sys._MEIPASS 变量
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 1. 加载 YOLO11 姿态检测模型
app_path = get_app_path()
model_path = os.path.join(app_path, 'yolo11l-pose.pt')
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

# 2. 尝试打开摄像头，支持多种后端
print("正在尝试打开摄像头...")

# 优先使用 OBS 虚拟摄像头（索引 1），如果失败则尝试物理摄像头（索引 0）
camera_indices = [1, 0]  # 1=虚拟摄像头, 0=物理摄像头

cap = None
for camera_idx in camera_indices:
    print(f"尝试打开摄像头 {camera_idx}...")
    cap = cv2.VideoCapture(camera_idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"成功! 使用摄像头 {camera_idx}")
            break
        else:
            cap.release()
    cap = None

if cap is None or not cap.isOpened():
    print("\n错误: 无法打开摄像头!")
    print("请检查:")
    print("1. 如果使用 OBS 虚拟摄像头，请确保在 OBS 中已启动虚拟摄像机")
    print("2. 如果使用物理摄像头，请确保未被其他程序占用")
    print("3. 摄像头驱动是否正常")
    exit(1)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # 3. 使用 YOLO11 进行推理
    # persist=True 用于跨帧跟踪同一个人的编号
    results = model.track(frame, persist=True, verbose=False)

    for r in results:
        if r.keypoints is not None:
            # 获取人体框和关键点数据
            boxes = r.boxes.xywh.cpu().numpy()  # [x, y, w, h]
            keypoints = r.keypoints.data.cpu().numpy()  # [person_idx, landmark_idx, x,y,conf]

            for i, box in enumerate(boxes):
                x, y, w, h = box

                # --- 判定算法 1: 长宽比判定 ---
                # 如果宽度 w 大于 高度 h，说明人是横向躺着的
                aspect_ratio = w / h

                # --- 判定算法 2: 关键点相对高度 ---
                # 获取鼻子(index 0) 和 脚踝(index 15, 16) 的 Y 坐标
                person_kpts = keypoints[i]
                nose_y = person_kpts[0][1]
                # 取两只脚踝的平均高度
                ankle_y = (person_kpts[15][1] + person_kpts[16][1]) / 2

                # 垂直距离
                vertical_dist = ankle_y - nose_y

                # 综合判定逻辑
                if aspect_ratio > 1.2 or vertical_dist < (h * 0.3):
                    status = "FALL DETECTED!"
                    color = (0, 0, 255)  # 红色警告
                    
                    # 发送跌倒报警通知
                    import time
                    message = f"【跌倒检测报警】\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n状态: 检测到人员跌倒\n请及时查看监控画面！"
                    notifier.send_notification(message, notification_config)
                else:
                    status = "Normal"
                    color = (0, 255, 0)  # 绿色正常

                # 画框和文字显示
                cv2.rectangle(frame, (int(x - w / 2), int(y - h / 2)),
                              (int(x + w / 2), int(y + h / 2)), color, 2)
                cv2.putText(frame, f"{status}",
                            (int(x - w / 2), int(y - h / 2) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    # 显示画面
    cv2.imshow("YOLO11 Fall Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
