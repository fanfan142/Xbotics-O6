# Xbotics O6 控制台

用于控制灵心巧手 O6 的 Windows 桌面程序，包含：

- 摄像头跟随
- 猜拳互动
- 固定手势控制
- OpenClaw 离线调用提示词
- 完整打包与分发流程

这个仓库的目标不是做底层 SDK，而是提供一个**可运行、可打包、可发给学员**的 O6 控制台工程。

---

## 目录结构

```text
Xbotics-O6/
├── app/                    # GUI 与业务逻辑
├── assets/                 # 模型与静态资源
├── runtime/                # 运行配置
├── prompt_version/         # 给 OpenClaw 使用的离线控制包模板
├── build_dist.py           # 一键打包脚本
├── xbotics2.spec           # PyInstaller 配置
├── main.py                 # 程序入口
├── requirements.txt        # 运行依赖
└── README.txt              # 分发包内附带说明
```

---

## 环境要求

### 操作系统

- Windows 10 / 11

### Python

推荐：

- Python 3.11+

说明：

- 本仓库已在当前打包链路中使用 Python 3.11 完成构建。
- `prompt_version/tools/o6_bridge.py` 的脚本模式建议 Python 3.12+。
- 源码仓库默认提交的是 **可重建模板**，不默认提交 `o6_bridge.exe`。
- 如果你在分发阶段额外放入 `o6_bridge.exe`，则学员侧可以不依赖本机 Python。

### 硬件

- O6 灵巧手
- PCAN-USB
- USB 摄像头
- Windows PC

---

## 从源码运行

### 1. 克隆仓库

```bash
git clone https://github.com/fanfan142/Xbotics-O6.git
cd Xbotics-O6
```

### 2. 创建虚拟环境

PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
pip install -r requirements.txt
```

### 4. 准备 linkerbot SDK

运行前请先确认当前 Python 环境能导入：

```powershell
python -c "from linkerbot import O6; print('linkerbot ok')"
```

如果这里失败，说明当前环境还没有准备好 O6 底层 SDK。

### 5. 检查运行配置

编辑：

- `runtime/config.json`

Windows + PCAN 常见配置：

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
  }
}
```

### 6. 启动程序

```powershell
python main.py
```

---

## 程序内 OpenClaw 按钮说明

程序里的 **“OpenClaw 调用说明”** 按钮会：

1. 读取当前分发目录下的 `prompt_version/PROMPT.md`
2. 自动把 `__PROMPT_VERSION_DIR__` 替换成当前真实绝对路径
3. 弹出一份可直接复制给 OpenClaw 的完整提示词

也就是说：

- 如果你运行的是打包后的控制台，按钮里显示的是**当前包内可直接使用**的提示词
- 不需要手改 prompt 路径
- 更适合学员直接复制使用

---

## prompt_version 是做什么的

`prompt_version/` 是给 OpenClaw 用的离线控制包模板，里面包含：

- `PROMPT.md`：发给 OpenClaw 的最终提示词模板
- `tools/o6_bridge.py`：脚本版 bridge
- `run_bridge.ps1` / `run_bridge.cmd`：快捷入口
- `o6_openclaw_config.template.json`：配置模板
- `vendor/linkerbot/`：脚本模式所需 SDK 副本

说明：

- 仓库中默认提交的是源码模板，不默认提交 `tools/o6_bridge.exe`
- 如果你要做完全离线分发，可以在出包阶段额外放入 `o6_bridge.exe`

分发给学员时，推荐使用**打包产物中的顶层 `prompt_version/`**，不要让学员直接从源码仓库里东拼西凑。

---

## 一键打包完整控制台

安装 PyInstaller：

```powershell
pip install pyinstaller
```

执行：

```powershell
python build_dist.py
```

打包完成后会生成：

- `dist/Xbotics_O6控制台/`
- `dist/Xbotics_O6控制台.zip`

其中：

- `Xbotics_O6控制台.exe`：主程序
- `_internal/`：运行依赖
- `prompt_version/`：给 OpenClaw 用的离线控制包
- `README.txt`：分发包内说明

这就是推荐发给学员的最终交付物。

如果你要做完全离线分发，可在出包阶段把额外构建好的 `o6_bridge.exe` 放入 `dist/Xbotics_O6控制台/prompt_version/tools/`。

---

## 推荐交付方式

### 给学员

直接发：

- `dist/Xbotics_O6控制台.zip`

### 给 OpenClaw

让用户：

1. 解压完整控制台包
2. 打开程序
3. 点击 **OpenClaw 调用说明**
4. 复制弹窗中的完整提示词
5. 发给 OpenClaw

这是当前最稳的使用路径。

---

## 常见问题

### 1. 程序里显示 O6 未连接

优先检查：

- O6 是否上电
- PCAN-USB 是否插好
- `runtime/config.json` 中的 `side` 是否正确
- `interface_name` 是否真的是当前机器上的通道名（如 `PCAN_USBBUS1`）
- 当前 Python 环境是否能单独导入 `linkerbot`

### 2. OpenClaw 调不通 bridge

先用分发包里的 `prompt_version` 自检：

```powershell
.\run_bridge.ps1 --json doctor
.\run_bridge.ps1 --json state
.\run_bridge.ps1 --json pose --preset open_hand
```

如果返回里出现：

- `pcan.available_channels = []`
- `pcan.raw_bus_open = false`

优先说明当前系统没有枚举到可用 PCAN 通道，应先检查：

- PCAN-USB 是否插好
- 驱动是否正常
- PCAN-View 是否能看到设备
- 通道是否被其他程序占用

### 3. 学员电脑没有 Python

如果你的分发包里额外放入了：

- `prompt_version/tools/o6_bridge.exe`

那么 OpenClaw 可以优先走 exe，不依赖学员本机 Python。

如果没有这个 exe，则使用仓库默认提供的 `o6_bridge.py` 模板时，需要准备兼容的 Python 环境。

### 4. `PROMPT.md` 里的路径还是占位符

这是源码模板的正常表现。

真正给 OpenClaw 用时，推荐通过程序里的 **OpenClaw 调用说明** 按钮复制；按钮会自动把占位符替换成真实路径。

---

## 当前仓库定位

这个仓库现在包含两条完整链路：

1. **GUI 主链路**：运行控制台，直接控制 O6
2. **OpenClaw 链路**：通过 `prompt_version/` 和 bridge 给 OpenClaw 使用

所以它既是：

- 一个可运行的 O6 控制台项目
- 也是一个可打包、可分发、可教学交付的最小源码仓库

---

## License

本项目使用 MIT License，详见 `LICENSE`。

第三方依赖和上游 SDK 仍遵循各自许可证。