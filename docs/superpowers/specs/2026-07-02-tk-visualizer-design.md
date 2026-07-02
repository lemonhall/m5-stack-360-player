# Tk 姿态可视化设计

## 目标

构建一个 PC 端 Python 小工具，用 tkinter 将 M5StickC Plus2 渲染成橙黄色 3D 小棒/长方体，并让它的姿态跟随实时 BLE 遥测。

## 范围

- 添加 `m5-visualizer` 控制台脚本。
- 复用已有 BLE 通知 transport、telemetry parser 和 calibration state。
- GUI 只使用 Python 标准库组件：`tkinter` 和 `Canvas`。
- 渲染一个简单的长方体透视投影，并显示轻量状态文本。
- 不包含 PotPlayer 控制、鼠标模拟、OpenGL 和外部 GUI 依赖。

## 交互

首屏就是可用的可视化窗口。窗口包含深色画布、小坐标轴和橙黄色小棒/长方体。收到 `ypr` 遥测后长方体随姿态旋转。按下 M5 主按钮仍通过已有 `CalibrationState` 更新中心校准；当相对姿态可用时，可视化渲染相对姿态。

## 架构

- `pc_receiver.visualization`：纯几何和投影函数。该模块不依赖 BLE 或 tkinter，并由单元测试覆盖。
- `pc_receiver.visualizer_app`：tkinter 窗口、BLE worker 线程、queue 交接和重绘循环。
- 已有 `pc_receiver.transport.iter_ble_notifications` 仍作为 BLE 数据源。
- 已有 `pc_receiver.telemetry.parse_telemetry` 仍作为协议解析器。
- 已有 `pc_receiver.calibration.CalibrationState` 仍负责中心姿态。

## 数据流

`BLE notification -> parse_telemetry -> CalibrationState.update -> VisualizerSnapshot -> Tk queue -> Canvas redraw`

BLE 循环在后台线程里运行自己的 asyncio loop。Tk 留在主线程。后台线程只向标准 `queue.Queue` 投递不可变快照和错误/状态消息。

## 错误处理

- 缺少 `--address` 时通过 argparse 退出。
- BLE 异常显示在窗口状态行并打印到 stderr。
- 畸形包会被跳过并计入 parse error。
- 尚未收到数据包时，画布显示中性小棒和 `waiting`。

## 验证

- 单元测试覆盖 yaw/pitch/roll 旋转行为和 2D 投影输出。
- 既有 parser/calibration 测试保持不变。
- 手动/live 验证命令：
  `uv run --extra ble m5-visualizer --address 0C:8B:95:B4:7B:5A`
