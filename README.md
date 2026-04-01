# Xbotics O6 控制台

一个面向 **灵心巧手 O6 灵巧手** 的 Python 图形控制程序，支持：

- 摄像头手势跟随
- 猜拳互动
- 预设姿态一键执行
- 基于 PCAN-USB 的 CAN 总线控制

项目目标不是做成通用 SDK，而是提供一个**清晰、可运行、方便二次开发**的 O6 桌面样例程序。

---

## 1. 项目简介

本项目将三个能力整合到一个 PySide6 桌面应用中：

1. **设备控制**：通过 `linkerbot-python-sdk` 控制 O6 灵巧手关节
2. **视觉识别**：通过 MediaPipe Hands 提取手部 21 点关键点
3. **动作映射**：把视觉特征映射为 O6 六个关节的目标角度

适合以下场景：

- O6 灵巧手快速演示
- 相机手势交互实验
- 基于官方/现有 SDK 做 GUI 控制样例
- 作为后续 ROS、机器人系统或上位机的原型

---

## 2. 功能列表

### 2.1 摄像头跟随

读取摄像头画面，检测手部关键点，经过三段标定后，把手指弯曲和拇指摆动映射到 O6 关节角度。

### 2.2 猜拳互动

识别用户的石头 / 剪刀 / 布手势，控制 O6 输出克制手势。

### 2.3 预设姿态控制

内置若干固定姿态，例如：

- 张开
- 半开
- 握拳
- 点赞
- OK
- 剪刀手
- 数字手势
- 捏合 / 强力抓取

---

## 3. 环境要求

### 3.1 操作系统

当前主要按 **Windows 10 / Windows 11** 使用场景整理。

### 3.2 Python 版本

建议：

- **Python 3.10 ~ 3.11**

说明：

- `PySide6`、`MediaPipe`、`OpenCV` 在这个范围内兼容性更稳
- 如果你使用更高版本 Python，建议先自行验证依赖是否都能正常安装

### 3.3 硬件要求

| 硬件 | 说明 |
| --- | --- |
| O6 灵巧手 | 被控设备 |
| PCAN-USB / 同类 CAN 设备 | 用于和 O6 通信 |
| USB 摄像头 | 用于手势识别 |
| Windows PC | 建议 4GB+ 内存 |

### 3.4 驱动与运行前置条件

运行前请确保：

1. 已安装 **PCAN 驱动** 或你的 CAN 设备对应驱动
2. O6 已正常供电并接入 CAN 总线
3. 摄像头可被系统识别
4. Python 环境已安装项目依赖

---

## 4. 依赖说明

项目依赖定义在 `requirements.txt`：

| 依赖 | 作用 |
| --- | --- |
| PySide6 | 桌面 GUI |
| opencv-python | 摄像头采集、图像处理 |
| mediapipe | 手部关键点检测 |
| numpy | 数值计算 |
| python-can | CAN 通信底层支持 |
| pydantic | 配置模型 |
| scipy | 数值/插值相关支持 |

安装命令：

```bash
pip install -r requirements.txt
```

---

## 5. SDK 来源与参考

### 5.1 O6 控制 SDK

本项目的 O6 控制逻辑基于 `linkerbot-python-sdk` 的接口方式封装。

在代码中主要使用：

- `from linkerbot import O6`
- `hand.angle.set_angles(...)`
- `hand.get_snapshot()`

你需要自行准备可用的 `linkerbot` Python 环境或 SDK 安装来源。

当前仓库中的 `app/services/o6_service.py` 只是对 SDK 做了一层**更适合 GUI 调用**的服务封装，不是重新实现底层协议。

命名约定如下：

- 对外展示名：`Xbotics O6`
- GitHub 仓库名：`Xbotics-O6`
- 本地校准目录：`.xbotics_o6`

### 5.2 MediaPipe Hands

本项目使用 MediaPipe Hands 做单手 21 点关键点检测。

用途包括：

- 识别石头 / 剪刀 / 布
- 提取手指弯曲角度
- 提取拇指摆动特征
- 驱动实时跟随

参考：

- https://google.github.io/mediapipe/solutions/hands

### 5.3 python-can

本项目通过 `python-can` 所支持的接口体系完成 CAN 层通信适配。

参考：

- https://python-can.readthedocs.io/

---

## 6. 仓库结构

```text
Xbotics-O6/
├── app/
│   ├── constants.py
│   ├── models/
│   │   └── config_models.py
│   ├── services/
│   │   ├── camera_service.py
│   │   ├── camera_teleop.py
│   │   └── o6_service.py
│   └── ui/
│       └── main_window.py
├── assets/
│   └── hand_landmarker.task
├── runtime/
│   └── config.json
├── main.py
├── requirements.txt
└── README.md
```

### 结构说明

- `main.py`：程序入口
- `app/ui/main_window.py`：主界面、交互逻辑、共享摄像头线程
- `app/services/o6_service.py`：O6 设备连接、角度写入、姿态执行
- `app/services/camera_service.py`：摄像头读取、MediaPipe 检测、猜拳识别
- `app/services/camera_teleop.py`：标定、特征提取、关节映射、平滑输出
- `runtime/config.json`：O6 设备侧配置
- `assets/hand_landmarker.task`：MediaPipe 模型文件

---

## 7. 系统流程

### 7.1 主控制链路

```text
摄像头帧
  ↓
CameraService
  ↓
MediaPipe Hands
  ↓
手部关键点 / 手势结果
  ↓
CameraTeleop（标定 + 特征映射 + 平滑）
  ↓
O6Service
  ↓
linkerbot SDK
  ↓
O6 灵巧手
```

### 7.2 GUI 信号关系

```text
MainWindow
  ├─ 共享摄像头控制
  ├─ CameraPanel（跟随）
  ├─ RSPanel（猜拳）
  └─ GestureGrid（预设动作）
```

### 7.3 跟随模式信号流程

```text
用户手部动作
  ↓
摄像头采集
  ↓
MediaPipe 输出 21 点关键点
  ↓
提取五指弯曲角 + 拇指摆动特征
  ↓
和标定数据做映射
  ↓
输出 6 维关节角（0~100）
  ↓
发送到 O6
```

---

## 8. O6 关节定义

本项目按 6 维角度控制 O6：

| 索引 | 关节名 | 说明 |
| --- | --- | --- |
| 0 | 拇指弯曲 | 拇指屈伸 |
| 1 | 拇指侧摆 | 拇指外展 / 内收 |
| 2 | 食指 | 食指弯曲 |
| 3 | 中指 | 中指弯曲 |
| 4 | 无名指 | 无名指弯曲 |
| 5 | 小指 | 小指弯曲 |

角度使用 `0 ~ 100` 的归一化范围，而不是直接暴露底层原始值。

---

## 9. 拉库后如何运行

### 9.1 克隆仓库

```bash
git clone https://github.com/fanfan142/Xbotics-O6.git
cd Xbotics-O6
```

### 9.2 创建虚拟环境

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Windows CMD

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 9.3 安装依赖

```bash
pip install -r requirements.txt
```

### 9.4 准备 O6 SDK 环境

如果你的环境里还没有可用的 `linkerbot` 包，需要先安装或配置对应 SDK。

你可以先验证：

```bash
python -c "from linkerbot import O6; print('linkerbot ok')"
```

如果这里报错，说明当前 Python 环境还没有准备好 O6 SDK。

### 9.5 检查配置文件

编辑：

- `runtime/config.json`

默认内容示例：

```json
{
  "o6": {
    "side": "right",
    "interface_name": "PCAN_USBBUS1",
    "interface_type": "pcan",
    "default_speed": 80,
    "default_acceleration": 60,
    "timeout_ms": 600,
    "force_timeout_ms": 1200
  },
  "ui": {
    "theme": "dark",
    "window_title": "Xbotics O6 控制台",
    "window_width": 1440,
    "window_height": 920
  }
}
```

重点确认：

- 当前唯一运行配置文件位置是 `runtime/config.json`
- `side` 是否和你的设备一致（`left` / `right`）
- `interface_name` 是否和你的 PCAN 设备名一致
- `interface_type` 是否和当前驱动环境一致

如果你看到旧截图、旧笔记或旧版本文档里写的是 `assets/config.json`，那已经是过时位置；当前仓库统一使用 `runtime/config.json`。

### 9.6 启动程序

```bash
python main.py
```

---

## 10. 使用方法

### 10.1 预设姿态控制

启动程序后，如果 O6 连接成功，点击左侧按钮即可执行对应姿态。

### 10.2 摄像头跟随

校准数据默认保存在用户目录下：

- 新路径：`~/.xbotics_o6/calibration.json`
- 兼容旧路径：`~/.xbotics3/calibration.json`

如果你以前用过旧版本，程序会优先兼容已有的旧标定文件。


1. 连接 O6 和摄像头
2. 点击“启动摄像头”
3. 点击“启动跟随”
4. 按顺序进行：
   - 张开标定
   - 握拳标定
   - 拇指内收标定
5. 标定完成后开始实时跟随

### 10.3 猜拳互动

1. 启动摄像头
2. 切换到“猜拳互动”标签页
3. 点击“开始猜拳”
4. 对着摄像头出拳
5. 程序识别后控制 O6 出对应克制手势

---

## 11. 常见问题

### Q1：`ModuleNotFoundError: No module named 'linkerbot'`

说明当前 Python 环境没有安装 O6 SDK。

处理方法：

- 先确认你使用的是正确虚拟环境
- 再安装或配置 `linkerbot-python-sdk`
- 用下面命令验证：

```bash
python -c "from linkerbot import O6; print('ok')"
```

### Q2：程序启动了，但显示 O6 未连接

常见原因：

- O6 没供电
- CAN 线连接异常
- PCAN 驱动未安装
- `runtime/config.json` 中 `interface_name` 不匹配
- 左右手 `side` 配置错误

建议排查顺序：

1. 先确认设备供电
2. 再确认驱动安装
3. 再确认 `interface_name`
4. 最后检查 SDK 单独控制是否正常

### Q3：摄像头无法打开

可能原因：

- 摄像头被微信 / QQ / 浏览器 / 其他软件占用
- 当前索引不是正确摄像头
- OpenCV 权限或驱动异常

建议：

- 关闭其他占用摄像头的软件
- 更换摄像头索引
- 重新插拔摄像头

### Q4：手势识别不稳定

可能原因：

- 光线不足
- 背景干扰过多
- 手没有完整进入画面
- 标定过程姿态不稳定

建议：

- 保证手部清晰、单手入镜
- 重新做三段标定
- 跟随时保持摄像头位置稳定

### Q5：猜拳页能看到画面，但不出结果

可能原因：

- 手势保持时间不够
- 手部没有完整进入取景区域
- 检测到的手势在连续帧中不稳定

建议：

- 出拳后保持 1~2 秒
- 尽量只保留一只手在画面中
- 增加光照

### Q6：跟随动作发抖或不够平滑

原因通常是：

- 手部检测本身抖动
- 标定样本不稳定
- 当前摄像头视角变化较大

当前程序已经做了：

- EMA 平滑
- Deadband 抑制小抖动

如果还不理想，可以继续调整 `app/services/camera_teleop.py` 中的平滑参数。

---

## 12. 已知限制

- 当前主要面向 Windows + PCAN 场景整理
- 依赖外部 O6 SDK 环境，不是完全独立开箱即用
- 手势跟随是样例级方案，不是工业级遥操作系统
- 目前以单手识别为主

---

## 13. 后续可扩展方向

- 增加更多手势模板
- 把姿态库独立成配置文件
- 支持录制 / 回放动作序列
- 支持多种 CAN 接口
- 提供无 GUI 的命令行模式
- 提供 ROS / WebSocket 桥接接口

---

## 14. 参考资料

- 灵心巧手官网：https://www.lingxinqiaoshou.com/
- MediaPipe Hands：https://google.github.io/mediapipe/solutions/hands
- python-can 文档：https://python-can.readthedocs.io/
- PCAN-USB：https://www.peak-system.com/PCAN-USB.199.0.html

如果你知道更准确的 O6 Python SDK 官方仓库地址，欢迎补充到本 README。

---

## 15. 协议

当前仓库暂未附带单独的 `LICENSE` 文件。

如果你计划长期公开维护，建议尽快补充正式许可证（例如 MIT），这样仓库的复用边界会更清晰。
