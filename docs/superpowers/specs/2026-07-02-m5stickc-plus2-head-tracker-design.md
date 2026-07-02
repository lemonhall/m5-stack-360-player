# M5StickC Plus2 头部姿态传感器链路设计

日期：2026-07-02

## 范围

本设计覆盖第一阶段：M5StickC Plus2 固定在眼镜上后，把姿态和原始 IMU 数据通过蓝牙传回 Windows PC。PC 端实时显示、写 JSONL 日志，并在用户按下 M5 主按钮时完成 PC 端零点校准。

本阶段不控制 PotPlayer，不模拟鼠标拖拽，不做播放器窗口识别。

## 推荐方案

推荐路线：基于 M5StickC Plus2 官方 IMU/cube 示例派生固件，保留屏幕上的 cube 可视化，只新增蓝牙遥测发送模块。PC 端以 Python `bleak` 作为 BLE GATT 通知接收器，并把传输层封装成可替换边界。

选择理由：

- 官方示例已经证明 IMU 初始化和 cube 可视化可用，能减少硬件层误判。
- BLE GATT 通知适合作为结构化遥测通道。
- JSON 文本和 JSONL 日志便于人工检查、回放和后续分析。
- PC 端校准比 M5 端校准更透明，原始姿态不会被污染。

## 备选方案

### 蓝牙 SPP / COM

优点是调试直观，PC 端用串口读取即可。缺点是 Windows 蓝牙串口配对和 COM 口稳定性不一定好，且后续结构化服务扩展不如 BLE 清晰。保留为 BLE 受阻时的降级路线。

### 二进制 BLE 包

优点是包短、效率高。缺点是第一阶段难以直接观察，日志需要专门解码，调试成本高。v1 不采用。

### 在 M5 端完成零点校准

优点是 PC 端简单。缺点是会让原始姿态和相对姿态混在一起，后续排查漂移与映射问题不够透明。v1 不采用。

## 架构

```text
M5StickC Plus2
  官方 IMU/cube 示例
    -> IMU read / pose update
    -> screen cube render（保持不变）
    -> telemetry builder
    -> BLE GATT notify（JSON text）

Windows PC
  BLE transport adapter（bleak）
    -> JSON decoder
    -> center calibration state
    -> terminal live view
    -> JSONL recorder
```

## 数据包

第一版遥测包使用 JSON 文本。建议字段：

```json
{
  "seq": 42,
  "ms": 123456,
  "ypr": [12.3, -4.5, 1.2],
  "quat": [0.99, 0.01, 0.02, 0.03],
  "acc": [0.01, 0.02, 0.98],
  "gyro": [0.1, -0.2, 0.0],
  "btn": 0
}
```

`ypr` 和 `quat` 不要求 v1 两者同时存在；拿到官方示例后，如果两者成本都低，则两者都发。`acc`、`gyro`、`btn`、`seq`、`ms` 必须存在。

## 校准

M5 主按钮只作为事件来源。PC 端收到按下事件时记录当前姿态为 `center_pose`。后续显示：

- absolute pose：M5 发来的原始融合姿态。
- relative pose：当前姿态相对于 `center_pose` 的相对姿态。

这样后续映射播放器时使用相对姿态，底层日志仍保留原始事实。

## 错误处理

- BLE 未发现设备：PC 程序显示可搜索到的候选设备，并以非零退出码结束。
- BLE 断开：PC 程序记录断开事件，尝试有限次重连；重连策略在 v1 计划中测试。
- JSON 解析失败：PC 程序记录原始文本和错误，不更新校准状态。
- 姿态字段缺失：PC 程序把该包标为 invalid，不用于校准。

## 测试策略

- 固件侧先用可编译测试或静态检查验证遥测 JSON 字段构造。
- PC 侧用单元测试验证 JSON 解析、按钮校准、相对姿态计算、JSONL 写入。
- E2E 使用可重复的模拟 BLE 数据源覆盖 PC 接收流程；真实 M5 连接作为人工/硬件验证项记录证据。

## 成功标准

- 官方 cube 可视化保留。
- PC 能收到 BLE 通知并显示遥测。
- JSONL 日志每行可独立解析。
- 主按钮触发 PC 端中心姿态更新。
- v1 不包含 PotPlayer 控制代码。
