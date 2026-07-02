# M5StickC Plus2 传感器链路实现计划

> **给 agentic worker 的要求：**实现本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。步骤使用 checkbox（`- [ ]`）语法追踪。

**目标：**构建 v1 传感器链路：M5StickC Plus2 通过 BLE 发送 JSON IMU 遥测，Windows PC 接收端负责解析、显示、记录和校准。

**架构：**PC 代码是一个小型 Python 包，包含 parser、calibration state、JSONL recorder、BLE transport 和 CLI 模块。固件是基于官方 M5StickCPlus2 IMU API 的 PlatformIO Arduino 工程，遥测构造与 BLE 通知、显示代码分离。

**技术栈：**Python 3.13、`uv`、`pytest`、`bleak`、PlatformIO、Arduino ESP32、M5StickCPlus2/M5Unified。

---

### 任务 1：源码基线

**文件：**
- 创建：`docs/hardware/m5stickc-plus2-example-source.md`
- 创建：`docs/superpowers/plans/2026-07-02-m5stickc-plus2-sensor-link-implementation.md`

- [x] **步骤 1：记录官方来源**

记录官方 M5Stack 源码 URL、库版本和 API 观察。

- [x] **步骤 2：验证文档文件可读**

运行：`rg --files docs`
预期：列出 PRD、v1 计划、设计规格、来源记录和本实现计划。

### 任务 2：PC 接收端测试优先

**文件：**
- 创建：`tests/test_telemetry.py`
- 创建：`tests/test_calibration.py`
- 创建：`tests/test_jsonl_recorder.py`
- 创建：`tests/test_simulated_ble_flow.py`

- [ ] **步骤 1：编写失败测试**

测试必须覆盖有效遥测、非法 JSON、缺失字段、校准中心更新、JSONL 写入和模拟通知流程。

- [ ] **步骤 2：运行红灯测试**

运行：`uv run pytest`
预期：失败，因为 `pc_receiver` 包尚不存在。

### 任务 3：PC 接收端实现

**文件：**
- 创建：`pyproject.toml`
- 创建：`pc_receiver/__init__.py`
- 创建：`pc_receiver/telemetry.py`
- 创建：`pc_receiver/calibration.py`
- 创建：`pc_receiver/recorder.py`
- 创建：`pc_receiver/transport.py`
- 创建：`pc_receiver/app.py`

- [ ] **步骤 1：实现最小代码**

实现 parser、validation、calibration state、JSONL recorder、模拟通知 runner 和 BLE transport 边界。

- [ ] **步骤 2：运行绿灯测试**

运行：`uv run pytest`
预期：全部测试通过。

### 任务 4：固件静态测试优先

**文件：**
- 创建：`tests/test_firmware_static.py`

- [ ] **步骤 1：编写失败的固件检查**

测试必须断言 `platformio.ini` 存在、固件包含 `M5StickCPlus2.h`、BLE notify 代码、JSON key、频率配置，且无 PotPlayer/Windows 控制字符串。

- [ ] **步骤 2：运行红灯固件检查**

运行：`uv run pytest tests/test_firmware_static.py`
预期：失败，因为固件文件尚不存在。

### 任务 5：固件实现

**文件：**
- 创建：`platformio.ini`
- 创建：`firmware/m5stickc_plus2_sensor_link/src/main.cpp`

- [ ] **步骤 1：实现 PlatformIO 固件**

创建使用官方 M5StickCPlus2 API 的 Arduino ESP32 工程。保留屏幕遥测可视化，并添加 BLE JSON 通知。

- [ ] **步骤 2：运行静态测试和构建**

运行：`uv run pytest tests/test_firmware_static.py`
预期：通过。

运行：`pio run`
预期：依赖解析后 exit code 0。

### 任务 6：最终验证

**文件：**
- 修改：`docs/plan/v1-index.md`
- 修改：`docs/plan/tashan-loop-log.md`

- [ ] **步骤 1：运行验证**

运行：`uv run pytest`
运行仓库可疑乱码/NUL 扫描。
运行：`rg -n "PotPlayer|mouse_event|SendInput|pyautogui|win32gui|win32api" .`

- [ ] **步骤 2：记录评审和交付状态**

更新 v1 索引中的证据、commit 和 push 尝试。如果没有 remote，则记录 `no_remote`。

## 自检

- 规格覆盖：REQ-0001-001 到 REQ-0001-008 均映射到任务。
- 占位符扫描：无 TBD/TODO 占位符。
- 类型一致性：PC parser 输出 `TelemetryPacket`；calibration 消费 `TelemetryPacket`；recorder 写 packet dict。
