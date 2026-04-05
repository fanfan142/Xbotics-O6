# Xbotics O6 控制台

Xbotics O6 控制台是一个用于控制灵心巧手 O6 的 Windows 桌面应用，提供图形化操作界面、摄像头手势交互能力，以及 OpenClaw 离线控制集成能力。

## 功能特性

- **摄像头跟随**：实时将手部动作映射到 O6 关节
- **猜拳互动**：识别石头/剪刀/布并驱动 O6 执行动作
- **手势控制**：提供固定姿态的快捷控制
- **OpenClaw 集成**：内置提示词生成入口，支持离线桥接调用
- **可打包发布**：提供 PyInstaller 打包脚本与分发目录结构

## 目录结构

```text
Xbotics-O6/
├── app/                    # GUI 与业务逻辑
├── assets/                 # 模型与静态资源
├── runtime/                # 运行配置
├── prompt_version/         # OpenClaw 离线控制包模板
├── build_dist.py           # 一键打包脚本
├── xbotics2.spec           # PyInstaller 配置
├── main.py                 # 程序入口
├── requirements.txt        # 运行依赖
└── README.txt              # 分发包内说明
```

## 环境要求

### 操作系统

- Windows 10 / 11

### Python

- 推荐 Python 3.12（3.11+ 也可）
- `prompt_version/tools/o6_bridge.py` 脚本模式建议 Python 3.12+

### 硬件

- O6 灵巧手
- PCAN-USB
- USB 摄像头

## 快速开始

### 1) 克隆仓库

```bash
git clone https://github.com/fanfan142/Xbotics-O6.git
cd Xbotics-O6
```

### 2) 创建并激活虚拟环境（PowerShell）

先查看本机可用 Python：

```powershell
py -0p
```

优先使用 3.12（若无 3.12，可把下方命令中的 `3.12` 替换为你本机已安装版本）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

若激活时报执行策略错误，可先执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3) 安装依赖

```powershell
pip install -r requirements.txt
```

### 4) 检查 O6 SDK 可用性

```powershell
python -c "import sys, pathlib; p=pathlib.Path('prompt_version/vendor').resolve(); sys.path.insert(0,str(p)); from linkerbot import O6; print('linkerbot ok')"
```

### 5) 配置运行参数

编辑 `runtime/config.json`，Windows + PCAN 常见配置如下：

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

### 6) 启动程序

```powershell
python main.py
```

## OpenClaw 集成

应用内的 **“OpenClaw 调用说明”** 按钮会读取 `prompt_version/PROMPT.md`，自动替换路径占位符 `__PROMPT_VERSION_DIR__`，并展示可直接复制的完整提示词。

`prompt_version/` 目录包含 OpenClaw 离线控制所需模板与工具：

- `PROMPT.md`
- `tools/o6_bridge.py`
- `run_bridge.ps1` / `run_bridge.cmd`
- `o6_openclaw_config.template.json`
- `vendor/linkerbot/`

仓库默认不包含 `tools/o6_bridge.exe`。如需完全离线运行，可在发布阶段额外放入该可执行文件。

## 打包发布

安装 PyInstaller：

```powershell
pip install pyinstaller
```

执行打包：

```powershell
python build_dist.py
```

产物路径：

- `dist/Xbotics_O6控制台/`
- `dist/Xbotics_O6控制台.zip`

其中包含主程序、运行依赖、`prompt_version/` 以及 `README.txt`。

## 常见问题

### O6 未连接

请优先检查：

- O6 是否上电
- PCAN-USB 是否连接正常
- `runtime/config.json` 中 `side` 与 `interface_name` 是否正确
- 当前 Python 环境是否可导入 `linkerbot`

### `No suitable Python runtime found`

通常是命令里指定的 Python 版本未安装（例如 `py -3.11` 但机器只有 3.12）。

处理方式：

1. 先执行 `py -0p` 查看可用版本
2. 用已安装版本创建 venv（例如 `py -3.12 -m venv .venv`）

### `.\.venv\Scripts\Activate.ps1` 找不到

通常是上一条 `py -x.y -m venv .venv` 没有成功执行，导致 `.venv` 未创建。

处理方式：

1. 先确认目录中存在 `.venv\Scripts\Activate.ps1`
2. 若不存在，先重建：`py -3.12 -m venv .venv`
3. 若存在但被策略拦截，先执行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` 后再激活

### `ModuleNotFoundError: linkerbot`

源码模式依赖仓库内 `prompt_version/vendor/linkerbot`。请确认：

1. 目录 `prompt_version/vendor/linkerbot` 存在
2. 从仓库根目录执行 `python main.py`
3. 若仍报错，用第 4 步的 SDK 检查命令验证导入路径

### OpenClaw bridge 调用失败

在 `prompt_version/` 目录中执行：

```powershell
.\run_bridge.ps1 --json doctor
.\run_bridge.ps1 --json state
.\run_bridge.ps1 --json pose --preset open_hand
```

若输出包含 `pcan.available_channels = []` 或 `pcan.raw_bus_open = false`，通常表示系统未枚举到可用 PCAN 通道，请检查驱动、设备连接及通道占用状态。

### `PROMPT.md` 仍显示占位符路径

源码模板中的占位符是预期行为。通过应用内 **“OpenClaw 调用说明”** 按钮生成的内容会自动替换为实际路径。

## License

本项目采用 MIT License，详见 `LICENSE`。  
第三方依赖与上游 SDK 仍遵循其各自许可证。
