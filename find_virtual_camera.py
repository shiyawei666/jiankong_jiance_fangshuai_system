import cv2

print("检测所有可用的摄像头...")
print("=" * 50)

for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"摄像头 {i}: 可用 (分辨率: {frame.shape[1]}x{frame.shape[0]})")
            cv2.imshow(f"Camera {i}", frame)
        else:
            print(f"摄像头 {i}: 设备存在但无法读取")
        cap.release()
    else:
        print(f"摄像头 {i}: 不可用")

print("=" * 50)
print("查看上面的窗口，找到 OBS 虚拟摄像头的画面")
print("记住对应的摄像头索引号，然后修改 main.py 中的 camera_indices")
print("按任意键关闭...")
cv2.waitKey(0)
cv2.destroyAllWindows()
