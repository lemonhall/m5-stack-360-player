# v1 Plan: Sensor Link

## Goal

交付 M5StickC Plus2 到 Windows PC 的第一版传感器数据链路：官方 IMU/cube 示例保留，M5 通过 BLE 发送 JSON 遥测，PC 端接收、实时显示、写 JSONL 日志，并支持主按钮零点校准。

## PRD Trace

- REQ-0001-001
- REQ-0001-002
- REQ-0001-003
- REQ-0001-004
- REQ-0001-005
- REQ-0001-006
- REQ-0001-007
- REQ-0001-008

## Scope

做：

- 查找并记录 M5StickC Plus2 官方 IMU/cube 示例来源。
- 建立可复现的固件工程。
- 在官方示例循环旁路新增遥测构造和 BLE 通知发送。
- 建立 Python PC 接收端，封装 BLE transport。
- 实现 JSON 解码、实时终端显示、JSONL recorder、PC 端校准状态。
- 编写单元测试、模拟 BLE E2E、真实硬件验收记录模板。

不做：

- 不控制 PotPlayer。
- 不调用鼠标或窗口控制 API。
- 不做 PC 端 GUI。
- 不承诺高于 60 Hz 的稳定发送。

## Acceptance

1. 固件工程可构建，构建命令 exit code 0。
2. M5 屏幕姿态可视化入口保留，真实硬件验收记录说明 cube 或等价可视化正常。
3. M5 遥测 JSON 包含 `seq`、`ms`、`acc`、`gyro`、`btn`，并包含 `ypr` 或 `quat` 至少一个姿态字段。
4. 默认发送频率配置为约 30 Hz，存在可调整配置项。
5. PC 端 parser 能拒绝非法 JSON、缺字段包和无姿态包。
6. PC 端按钮校准测试覆盖：按钮未按下不改变中心；按钮按下更新中心；相对姿态从新中心计算。
7. PC 端 JSONL writer 输出每行可独立 `json.loads` 的日志。
8. 模拟 BLE E2E 能驱动 PC 接收流程并断言实时状态与日志产物。
9. 真实硬件验收时能连接 BLE，连续收包不少于 60 秒，日志内有效包数量不低于期望频率的 80%。
10. 反作弊：`rg -n "PotPlayer|mouse_event|SendInput|pyautogui|win32gui|win32api" .` 不得命中 v1 控制逻辑。

## Files

预计创建或修改：

- `firmware/`：M5StickC Plus2 固件工程。
- `pc_receiver/`：Python PC 接收端包。
- `tests/`：单元测试和模拟 E2E。
- `logs/`：运行时日志目录，实际日志应被 `.gitignore` 忽略。
- `docs/hardware/`：真实 M5 验收记录和样例摘要。

## Steps

### M1: 官方示例和工程基线

1. 查找 M5StickC Plus2 官方 IMU/cube 示例源码。
2. 记录来源到 `docs/hardware/m5stickc-plus2-example-source.md`。
3. 决定原样导入 Arduino 工程或迁移到 PlatformIO。
4. 写最小构建检查。
5. 运行构建到绿。

预期验证：

```powershell
pio run
```

或：

```powershell
arduino-cli compile <firmware-project>
```

### M2: 固件遥测和 BLE 通知

1. 写遥测 JSON 构造测试或可编译检查。
2. 运行到红，确认字段缺失时测试失败。
3. 在官方示例循环中新增遥测构造和 BLE GATT notify。
4. 保留屏幕 cube 渲染路径不变。
5. 运行构建和字段检查到绿。

预期验证：

```powershell
pio run
```

并保留一条实际遥测样例，确认可被 JSON parser 解析。

### M3: PC 接收端、日志和校准

1. 写 Python 单元测试：JSON parser、校准状态、JSONL writer。
2. 写模拟 BLE E2E：模拟通知数据驱动 receiver。
3. 运行测试到红。
4. 实现 BLE transport adapter、decoder、terminal state、recorder、calibration。
5. 运行测试到绿。

预期验证：

```powershell
uv run pytest
```

### M4: 真实硬件验收

1. 烧录固件到 M5StickC Plus2。
2. 运行 PC receiver 连接 M5。
3. 连续采集不少于 60 秒。
4. 按下主按钮，确认相对姿态从中心附近开始变化。
5. 保存 JSONL 样例摘要和验收记录。
6. 执行 PotPlayer 禁入扫描。

预期验证：

```powershell
rg -n "PotPlayer|mouse_event|SendInput|pyautogui|win32gui|win32api" .
```

## Risks

- 官方示例位置或库版本不匹配：M1 先记录来源和构建方式，不先写遥测。
- BLE 在 Windows 上连接不稳定：transport 边界保持可替换，必要时通过 ECN 降级到串口或 USB。
- JSON 包超过 BLE 单次通知长度：优先减少可选字段或拆包，不能直接切二进制协议；若改变协议需写 ECN。
- 姿态字段不易从官方示例导出：先发送原始 IMU，再通过 ECN 决定是否补 Mahony/Madgwick。
- 真实硬件测试依赖设备连接：M3 必须用模拟 BLE E2E 保证 PC 逻辑可回归。
