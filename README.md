# Xbotics O6 控制台

基于 MediaPipe 手势识别与灵心巧手 O6 灵巧手的实时控制系统，支持摄像头跟随、猜拳互动和预设手势控制。

## 功能特性

- **摄像头跟随**：将摄像头前的实时手部动作映射到 O6 灵巧手关节角度
- **猜拳互动**：做出石头/剪刀/布手势，O6 自动出克制手势
- **手势控制**：15 种预设姿势一键执行
- **CAN 总线通信**：通过 PCAN-USB 接口控制 O6 灵巧手

## 硬件要求

| 设备 | 说明 |
|------|------|
| O6 灵巧手 | 灵心巧手 6 自由度灵巧手 |
| PCAN-USB | CAN 转 USB 适配器（PCAN-USB） |
| 摄像头 | 普通 USB 摄像头即可 |
| PC | Windows 10/11，4GB+ 内存 |

## 项目结构

```
xbotics3/
├── app/
│   ├── constants.py           # 项目路径常量
│   ├── models/
│   │   └── config_models.py   # 配置数据模型（Pydantic）
│   ├── services/
│   │   ├── camera_service.py  # 摄像头捕获 + MediaPipe 手势检测
│   │   ├── camera_teleop.py   # 标定逻辑 + 关节角度映射
│   │   └── o6_service.py      # O6 CAN 通信 + 预设姿势执行
│   └── ui/
│       └── main_window.py     # PySide6 GUI 主窗口
├── assets/
│   ├── config.json            # 运行时配置（CAN 接口等）
│   └── hand_landmarker.task   # MediaPipe 手部地标模型（7.8MB）
├── runtime/                   # 运行时生成文件（如校准数据）
├── main.py                    # 应用入口
└── requirements.txt           # Python 依赖
```

## 信号流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           主程序流程                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐   │
│  │   Camera     │────▶│  MediaPipe        │────▶│  CameraTeleop    │   │
│  │   Service    │     │  HandLandmarker   │     │  (标定+映射)      │   │
│  │  (OpenCV)    │     │  (21点地标)       │     │                  │   │
│  └──────────────┘     └───────────────────┘     └────────┬─────────┘   │
│                                                          │              │
│                                                          ▼              │
│                                                 ┌──────────────────┐    │
│                                                 │    O6Service     │    │
│                                                 │  (CAN 通信)      │    │
│                                                 └────────┬─────────┘    │
│                                                          │              │
│                                                          ▼              │
│                                                 ┌──────────────────┐    │
│                                                 │  O6 灵巧手       │    │
│                                                 │  (执行动作)      │    │
│                                                 └──────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 摄像头跟随标定流程

```
用户执行手势
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  1. 张开标定：采集手掌张开时的各关节角度 + 拇指摆幅       │
│  2. 握拳标定：采集握拳时的各关节角度                     │
│  3. 拇指内收标定：采集拇指贴近掌心时的摆幅               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
标定数据保存到 ~/.xbotics3/calibration.json
    │
    ▼
实时跟随时：根据当前手势角度在张开/握拳之间线性插值
```

## SDK 来源与参考

### linkerbot-python-sdk

O6 灵巧手的 Python 控制 SDK，来源：[灵心巧手 Python SDK](https://github.com/your-repo/linkerbot-python-sdk)

```python
from linkerbot import O6
from linkerbot.hand.o6.angle import O6Angle

# 创建 O6 实例
hand = O6(side="right", interface_name="PCAN_USBBUS1", interface_type="pcan")
hand.stop_polling()  # 停止自动轮询

# 设置关节角度（0-100 范围）
hand.angle.set_angles([50, 50, 50, 50, 50, 50])  # [拇指弯曲, 拇指侧摆, 食指, 中指, 无名指, 小指]

# 读取当前角度
snapshot = hand.get_snapshot()
print(snapshot.angle.angles.to_list())
```

**关节定义**（O6 灵巧手共 6 个自由度）：

| 索引 | 名称 | 说明 |
|------|------|------|
| 0 | 拇指弯曲 | 拇指指节弯曲 |
| 1 | 拇指侧摆 | 拇指侧向移动 |
| 2 | 食指 | 食指弯曲 |
| 3 | 中指 | 中指弯曲 |
| 4 | 无名指 | 无名指弯曲 |
| 5 | 小指 | 小指弯曲 |

### MediaPipe Hands

Google 开源的手部追踪 SDK，本项目用于实时提取 21 个手部地标。

参考文档：https://google.github.io/mediapipe/solutions/hands

### python-can

跨平台的 CAN 总线 Python 封装，本项目通过它与 PCAN-USB 适配器通信。

参考文档：https://python-can.readthedocs.io/

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/xbotics-o6.git
cd xbotics-o6
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 CAN 接口

编辑 `assets/config.json`：

```json
{
  "o6": {
    "side": "right",
    "interface_name": "PCAN_USBBUS1",
    "interface_type": "pcan",
    "default_speed": 80,
    "default_acceleration": 60,
    "timeout_ms": 600
  }
}
```

| 参数 | 说明 |
|------|------|
| side | `"right"` 或 `"left"`，左右手 |
| interface_name | PCAN 设备名，如 `PCAN_USBBUS1` |
| interface_type | CAN 接口类型，`pcan` |

### 5. 安装 PCAN 驱动

从 [PEAK-System](https://www.peak-system.com/) 下载并安装 PCAN-USB 驱动。

## 运行

```bash
python main.py
```

## 使用说明

### 摄像头跟随

1. 连接 O6 灵巧手（CAN 接口）
2. 选择摄像头并点击「启动摄像头」
3. 点击「启动跟随」
4. 依次进行标定：
   - 张开标定：保持手掌张开约 1 秒
   - 握拳标定：保持握拳约 1 秒
   - 拇指内收标定：保持拇指向掌心收拢约 1 秒
5. 标定完成后即可实时跟随手部动作

### 猜拳互动

1. 启动摄像头后切换到「猜拳互动」标签
2. 点击「开始猜拳」
3. 对着摄像头做出手势（石头/布/剪刀）
4. O6 会自动出克制你的手势

### 手势控制

直接点击预设姿势按钮，如「张开」「握拳」「点赞」等。

## 依赖说明

| 依赖 | 版本 | 说明 |
|------|------|------|
| PySide6 | ≥6.11.0 | Qt for Python，GUI 框架 |
| opencv-python | ≥4.12.0 | 摄像头捕获 |
| mediapipe | ≥0.10.33 | 手部地标检测 |
| numpy | - | 数值计算 |
| python-can | ≥4.6.1 | CAN 总线通信 |
| pydantic | ≥2.12.5 | 配置数据模型 |
| scipy | ≥1.15.3 | 科学计算 |

## 常见问题

**Q: 摄像头打不开**
A: 检查设备是否被其他程序占用，或在代码中调整摄像头索引。

**Q: O6 未连接**
A: 检查供电、CAN 接口连接，以及 `config.json` 中的 `interface_name` 是否正确。

**Q: 手势识别不准**
A: 保持光线充足，重新进行标定。

## 上传到 GitHub

### 方法一：命令行

```bash
# 1. 进入项目目录
cd xbotics3

# 2. 初始化 Git 仓库（如果还没有）
git init

# 3. 添加所有文件
git add .

# 4. 提交
git commit -m "Initial commit: Xbotics O6 Control Console"

# 5. 在 GitHub 创建新仓库后，添加远程仓库
git remote add origin https://github.com/你的用户名/xbotics-o6.git

# 6. 推送
git push -u origin main
```

### 方法二：GitHub Desktop

1. 打开 GitHub Desktop
2. File → Add Local Repository → 选择 `xbotics3` 文件夹
3. 点击 "Publish repository"
4. 填写仓库名称和描述
5. 选择 Private 或 Public
6. 点击 Publish

### 方法三：网页上传

1. 打开 https://github.com/new
2. 填写仓库名称：`xbotics-o6`
3. 选择 Public 或 Private
4. 不要勾选 "Initialize this repository with a README"
5. 点击 "Create repository"
6. 网页会显示 "push an existing repository from the command line"，按照指示操作：

```bash
git remote add origin https://github.com/你的用户名/xbotics-o6.git
git branch -M main
git push -u origin main
```

### 注意事项

- `.gitignore` 建议添加：
  ```
  __pycache__/
  *.pyc
  .venv/
  *.egg-info/
  .pytest_cache/
  .ruff_cache/
  build/
  dist/
  *.spec
  ```

## 协议

MIT License

## 参考链接

- [灵心巧手官网](https://www.lingxinqiaoshou.com/)
- [linkerbot-python-sdk](https://github.com/linkerbot/linkerbot-python-sdk)
- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands)
- [python-can 文档](https://python-can.readthedocs.io/)
- [PCAN-USB 驱动](https://www.peak-system.com/PCAN-USB.199.0.html)
