# prompt_version

这是给 OpenClaw 用的 **O6 控制离线包**。

目标很简单：
- 保留整个 `prompt_version/`
- 把 `PROMPT.md` 发给 OpenClaw
- 优先通过 `tools/o6_bridge.exe` 控制 O6
- 只有在 exe 不存在时，才退回 `tools/o6_bridge.py`

## 目录说明

- `tools/o6_bridge.exe`：优先使用的离线 bridge，可直接运行
- `tools/o6_bridge.py`：脚本版 bridge，作为兼容兜底
- `vendor/linkerbot/`：随包分发的 SDK 副本
- `PROMPT.md`：发给 OpenClaw 的最终提示词模板
- `o6_openclaw_config.template.json`：配置模板
- `run_bridge.ps1` / `run_bridge.cmd`：Windows 快速入口，优先调用 exe
- `requirements.txt`：仅脚本兜底模式下可能需要

## 系统要求

### 推荐方式

推荐直接使用随包自带的：

- `tools/o6_bridge.exe`

这样**不依赖学员本机 Python**，更适合离线教学分发。

### 脚本兜底方式

如果 `o6_bridge.exe` 丢失，再退回：

- `tools/o6_bridge.py`

此时才需要兼容的 Python 环境；`run_bridge.ps1` / `run_bridge.cmd` 会优先使用 `O6_BRIDGE_PYTHON`。

## 第一次配置

### 1. 复制配置模板

复制：

- `o6_openclaw_config.template.json`

为：

- `o6_openclaw_config.json`

### 2. 按平台修改配置

#### Windows + PCAN 示例

```json
{
  "side": "right",
  "interface_name": "PCAN_USBBUS1",
  "interface_type": "pcan",
  "default_speed": 80,
  "default_acceleration": 60,
  "timeout_ms": 600,
  "force_timeout_ms": 1200,
  "settle_sec": 1.2,
  "fast_timeout_ms": 200,
  "fast_settle_sec": 0.2,
  "collision_threshold_ma": 300
}
```

#### Ubuntu / Linux + SocketCAN 示例

```json
{
  "side": "left",
  "interface_name": "can0",
  "interface_type": "socketcan",
  "default_speed": 80,
  "default_acceleration": 60,
  "timeout_ms": 600,
  "force_timeout_ms": 1200,
  "settle_sec": 1.2,
  "fast_timeout_ms": 200,
  "fast_settle_sec": 0.2,
  "collision_threshold_ma": 300
}
```

### 3. 可选环境变量覆盖

如果你不想改配置文件，也可以临时覆盖：

#### Windows

```powershell
$env:CAN_INTERFACE = 'PCAN_USBBUS1'
$env:CAN_INTERFACE_TYPE = 'pcan'
$env:O6_SIDE = 'right'
$env:O6_FAST_MODE = '1'
```

#### Ubuntu / Linux

```bash
export CAN_INTERFACE=can0
export CAN_INTERFACE_TYPE=socketcan
export O6_SIDE=left
export O6_FAST_MODE=1
```

覆盖优先级：

1. 默认配置
2. `o6_openclaw_config.json`
3. 环境变量
4. 命令行参数

## 先自检

推荐顺序：

```powershell
.\run_bridge.ps1 --json doctor
.\run_bridge.ps1 --json state
.\run_bridge.ps1 --json pose --preset open_hand
.\run_bridge.ps1 --json list-presets
```

说明：
- `doctor`：环境与配置检查
- `state` 成功：说明 O6 状态读取正常
- `pose --preset open_hand` 成功：说明动作控制正常
- `version` / `doctor --probe` 可以补充做，但超时不应直接判定为未连接
- 如果 JSON 输出里出现 `pcan.available_channels` 为空，且 `pcan.raw_bus_open=false`，优先说明当前系统未枚举到可用 PCAN 通道，不要误判成提示词问题

## 常用命令

注意：全局参数要放在子命令前面。

```powershell
.\run_bridge.ps1 --json state
.\run_bridge.ps1 --json version
.\run_bridge.ps1 --json force
.\run_bridge.ps1 --json list-presets
.\run_bridge.ps1 --json keyword-help
.\run_bridge.ps1 --json pose --preset open_hand
.\run_bridge.ps1 --json finger --finger index --target 20
```

`finger` 和 `pose` 一样，会在检测到 fault 或温度偏高时默认阻止动作；确认继续时再加 `--allow-risky`。

## 输出格式

默认输出是适合人看的文本。

如果要给脚本、OpenClaw 二次解析，建议加 `--json`，并且把它放在子命令前面：

```powershell
.\run_bridge.ps1 --json doctor
.\run_bridge.ps1 --json state
.\run_bridge.ps1 --json pose --preset open_hand
```

当前 JSON 输出顶层都会带 `ok`。

## 风险边界

以下动作默认按高风险处理：

- `close_hand`
- `power_grip`
- `pinch_heavy`
- `hold`
- `fist`

另外这些情况也属于风险场景：

- 高速连续动作
- 抓未知、易碎、危险物体
- 当前状态出现 fault
- 当前温度偏高

如果你确认继续，才追加：

```powershell
python .\tools\o6_bridge.py pose --preset power_grip --allow-risky
```

碰撞检查：

```powershell
python .\tools\o6_bridge.py pose --preset close_hand --collision-check
python .\tools\o6_bridge.py pose --preset close_hand --collision-stop
```

注意：当前的碰撞检查是**动作前的基线扭矩检查**，不是动作执行过程中的实时急停。

如果 `--collision-stop` 触发，命令会返回非 0 退出码。

## 怎么接 OpenClaw

1. 先把这个目录复制到目标机器
2. 修改 `PROMPT.md` 里唯一的目录占位符
3. 把 `PROMPT.md` 内容发给 OpenClaw
4. 让它先执行 `doctor`

## 文件列表


- `tools/o6_bridge.py`
- `vendor/linkerbot/`
- `PROMPT.md`
- `README.md`
- `requirements.txt`
- `LICENSE.linkerbot.txt`
- `o6_openclaw_config.template.json`
- `run_bridge.ps1`
- `run_bridge.cmd`

## 常见问题

### 1. Python 版本不对

先看：

```powershell
python --version
```

只有在 `tools/o6_bridge.exe` 丢失、必须退回 `tools/o6_bridge.py` 时，才需要兼容 Python；当前脚本兜底模式至少需要 Python 3.12。

### 2. 导包失败

重新安装依赖：

```powershell
python -m pip install -r .\requirements.txt
```

### 3. CAN 接口不对

- Windows 常见：`PCAN_USBBUS1 + pcan`
- Ubuntu 常见：`can0 + socketcan`
- 如果 `doctor/state` 返回 `pcan.available_channels = []`，说明当前系统层面没有枚举到可用 PCAN 通道，应先检查 PCAN-USB、驱动、PCAN-View 和通道占用

### 4. 左右手不对

检查：
- `side`
- `O6_SIDE`

### 5. OpenClaw 执行不到脚本

通常是 `PROMPT.md` 里的目录路径没改对。

