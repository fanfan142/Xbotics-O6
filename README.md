# Xbotics O6 控制台

用于控制灵心巧手 O6 的 Python 桌面演示程序。

支持：

- 摄像头跟随
- 猜拳互动
- 预设手势控制
- 基于 PCAN-USB 的 CAN 通信

## 快速开始

```bash
git clone https://github.com/fanfan142/Xbotics-O6.git
cd Xbotics-O6
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 环境要求

### 操作系统

- Windows 10 / 11

### Python 版本

推荐：

- **Python 3.13**

说明：

- 当前依赖组合在 Python 3.13 下更合适
- 3.10 ~ 3.12 可以自行尝试，但 README 以 3.13 为准

### 硬件要求

| 硬件 | 说明 |
| --- | --- |
| O6 灵巧手 | 被控设备 |
| PCAN-USB | 用于和 O6 通信 |
| USB 摄像头 | 用于手势识别 |
| Windows PC | 建议 4GB+ 内存 |

## 依赖

安装：

```bash
pip install -r requirements.txt
```

主要依赖：

- PySide6
- opencv-python
- mediapipe
- numpy
- python-can
- pydantic
- scipy

## 上游 SDK

本项目通过 `linkerbot-python-sdk` 控制 O6。

代码里主要用到：

- `from linkerbot import O6`
- `hand.angle.set_angles(...)`
- `hand.get_snapshot()`

所以这个仓库不是底层 SDK，本质上是一个 **基于 linkerbot Python SDK 的 GUI 样例程序**。

## 仓库结构

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
└── LICENSE
```

## 控制流程

```text
摄像头帧
  ↓
CameraService
  ↓
MediaPipe Hands
  ↓
CameraTeleop（标定 + 特征映射 + 平滑）
  ↓
O6Service
  ↓
linkerbot SDK
  ↓
O6 灵巧手
```

## O6 关节定义

| 索引 | 关节名 | 说明 |
| --- | --- | --- |
| 0 | 拇指弯曲 | 拇指屈伸 |
| 1 | 拇指侧摆 | 拇指外展 / 内收 |
| 2 | 食指 | 食指弯曲 |
| 3 | 中指 | 中指弯曲 |
| 4 | 无名指 | 无名指弯曲 |
| 5 | 小指 | 小指弯曲 |

角度范围使用 `0 ~ 100`。

## 拉库后怎么运行

官网与参考：

- LinkerBot 官网：<https://www.linkerbot.cn/index>
- MediaPipe 资料：<https://chuoling.github.io/mediapipe/>


### 1. 克隆仓库

```bash
git clone https://github.com/fanfan142/Xbotics-O6.git
cd Xbotics-O6
```

### 2. 创建虚拟环境

PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

CMD：

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 准备 linkerbot SDK

先确认当前 Python 环境能导入：

```bash
python -c "from linkerbot import O6; print('linkerbot ok')"
```

如果报错，说明你当前环境还没准备好 linkerbot SDK。

### 5. 安装 PCAN 驱动

Windows 下到 PEAK-System 官方页面下载安装：

- Drivers 总页：<https://www.peak-system.com/support/downloads/drivers/>
- Driver Packages：<https://www.peak-system.com/support/downloads/drivers/driver-packages/>

建议安装：

- **Device Driver Setup 5.x for Windows**

安装后会有：

- PEAK-Settings
- PCAN-View

### 6. 确认 PCAN 接口名

打开 **PEAK-Settings** 或 **PCAN-View**，找到当前设备通道名，例如：

- `PCAN_USBBUS1`
- `PCAN_USBBUS2`

把这个名字填进配置文件的 `interface_name`。

如果换过 USB 口、重装过驱动，名字可能变化，连不上时请重新确认。

### 7. 修改配置文件

编辑：

- `runtime/config.json`

重点确认：

- `side`：`left` 或 `right`
- `interface_name`：例如 `PCAN_USBBUS1`
- `interface_type`：通常是 `pcan`

当前仓库唯一使用的运行配置文件位置是：

- `runtime/config.json`

### 8. 启动程序

```bash
python main.py
```

## 使用方法

### 预设手势

程序启动后，如果 O6 已连接，点击左侧按钮即可执行对应动作。

### 摄像头跟随

1. 连接 O6 和摄像头
2. 点击“启动摄像头”
3. 点击“启动跟随”
4. 依次做：
   - 张开标定
   - 握拳标定
   - 拇指内收标定
5. 标定完成后开始实时跟随

校准数据默认位置：

- 新路径：`~/.xbotics_o6/calibration.json`
- 兼容旧路径：`~/.xbotics3/calibration.json`

### 猜拳互动

1. 启动摄像头
2. 切到“猜拳互动”页
3. 点击“开始猜拳”
4. 对着摄像头出拳
5. 程序识别后控制 O6 出克制手势

## 常见问题

### 1. `ModuleNotFoundError: No module named 'linkerbot'`

说明：

- 当前虚拟环境里没有安装或配置 linkerbot SDK

处理：

```bash
python -c "from linkerbot import O6; print('ok')"
```

如果这句不通，先别管 GUI，先把 SDK 环境配通。

### 2. `pip install -r requirements.txt` 失败

常见原因：

- Python 版本不对
- 用错了解释器
- 没进虚拟环境
- 网络问题

处理：

```bash
python --version
pip --version
where python
```

优先确认当前是不是 **Python 3.13 + 当前虚拟环境**。

### 3. 程序启动了，但显示 O6 未连接

常见原因：

- O6 没供电
- CAN 线没接好
- PCAN 驱动没装
- `runtime/config.json` 里 `interface_name` 写错
- `side` 写错
- linkerbot SDK 本身还没单独跑通

建议按这个顺序排查：

1. 看设备有没有正常供电
2. 确认 PCAN 驱动已安装
3. 打开 **PEAK-Settings / PCAN-View** 看当前接口名
4. 对照修改 `runtime/config.json`
5. 再单独用 linkerbot SDK 做一次最小测试

### 4. 不知道 `interface_name` 该填什么

最直接的方法：

1. 安装 PEAK 驱动包
2. 打开 **PEAK-Settings** 或 **PCAN-View**
3. 找到当前 PCAN-USB 设备对应通道
4. 看显示名称是不是：
   - `PCAN_USBBUS1`
   - `PCAN_USBBUS2`
   - 其他类似名字
5. 把这个名字填进 `runtime/config.json`

如果你电脑只插了一个 PCAN-USB，常见就是：

- `PCAN_USBBUS1`

### 5. 已经装了驱动，但还是连不上

检查这些点：

- USB 口是否识别正常
- 线缆是否接反或松动
- 波特率 / 总线设置是否和设备一致
- 设备是否被别的软件占用
- 重插 USB 后接口名是否变化

如果装了驱动，建议顺手打开：

- **PEAK-Settings**：看设备是否存在
- **PCAN-View**：看通道是否可打开

如果这两个工具都看不到设备，先别怀疑你的 Python 代码，先处理驱动/硬件层。

### 6. 摄像头打不开

常见原因：

- 摄像头被微信、QQ、浏览器、会议软件占用
- 当前索引不是目标摄像头
- 驱动异常

处理：

- 关闭占用摄像头的软件
- 重新插拔摄像头
- 更换摄像头索引再试

### 7. 猜拳 / 跟随识别不稳定

常见原因：

- 光线太差
- 背景太乱
- 手没有完整进画面
- 出拳或标定时动作不稳定

处理：

- 手尽量完整入镜
- 保证单手、背景干净、光照充足
- 标定时每个动作保持约 1 秒
- 跟随时尽量不要频繁改变摄像头位置

### 8. 跟随动作发抖

这是视觉跟随类程序里最常见的问题，原因通常是：

- 手部检测抖动
- 标定不稳定
- 视角变化大

当前程序已经做了：

- EMA 平滑
- Deadband 抑制小幅变化

如果还想继续压抖动，可以改：

- `app/services/camera_teleop.py`

重点看：

- `SMOOTH_ALPHA`
- `DEADBAND`

### 9. 旧版本标定突然没了

现在默认校准目录是：

- `~/.xbotics_o6/calibration.json`

但程序兼容旧路径：

- `~/.xbotics3/calibration.json`

如果你以前标定过，升级后一般会优先读取旧文件。

如果没有读到，就检查两个目录下的文件是否真的存在。

## 如何尽快打包出同样的 exe

当前仓库里没有直接保留 PyInstaller 打包脚本，但你本地旧工程 `xbotics2` 里有现成打包方案：

- `F:\sim\灵心巧手\o6\o6_student_minipack\xbotics2\build_dist.py`
- `F:\sim\灵心巧手\o6\o6_student_minipack\xbotics2\xbotics2.spec`

从这两个文件看，原来的 exe 是通过 **PyInstaller** 打出来的，核心思路是：

1. 安装 PyInstaller
2. 准备好和运行环境一致的 Python、linkerbot、mediapipe、can、serial 等依赖
3. 用 `spec` 文件把 `assets/`、`runtime/` 和需要的第三方包一起打进发布目录
4. 再把整个发布目录压成 zip

### 最快的复现方式

如果你只是想尽快重新打出一个可分发 exe，最省事的方式不是从零写 spec，而是：

1. 复制 `xbotics2` 里的 `build_dist.py` 和 `xbotics2.spec`
2. 把其中路径和名称改成当前仓库版本
3. 在已经能正常运行 GUI 的同一套 Python 环境里执行：

```bash
python -m PyInstaller --noconfirm your.spec
```

### 打包前必须满足

- `python main.py` 已经能正常启动
- `from linkerbot import O6` 能导入
- `mediapipe`、`can`、`serial` 都已安装
- `assets/hand_landmarker.task` 和 `runtime/config.json` 已准备好

### 打包结果建议

建议最终发布结构保持和旧版一致：

```text
Xbotics_O6控制台/
├── Xbotics_O6控制台.exe
├── _internal/
├── assets/
└── runtime/
```

然后再把整个目录压缩成 zip 发 release。

## 协议

本项目使用 **MIT License**，详见 `LICENSE`。

第三方依赖和上游 SDK 仍遵循各自许可证。

## 参考

- LinkerBot 官网：https://www.linkerbot.cn/index
- MediaPipe：https://chuoling.github.io/mediapipe/
- python-can：https://python-can.readthedocs.io/
- PEAK 驱动下载：https://www.peak-system.com/support/downloads/drivers/
- PEAK Driver Packages：https://www.peak-system.com/support/downloads/drivers/driver-packages/
- PCAN handle 定义：https://docs.peak-system.com/API/PCAN-Basic.Net/html/459b03fc-f14e-4e58-81c8-430229f7b27e.htm
