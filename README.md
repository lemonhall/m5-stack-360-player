# M5StickC Plus2 头控 360 播放器

本项目把 M5StickC Plus2 当作固定在眼镜上的头部姿态传感器，通过 BLE 把姿态数据发到 Windows PC，再由 PC 端 GUI 播放器调用 libVLC 的 360 视角接口控制画面。

当前主线已经从最初的 PotPlayer 方向切到内嵌 VLC/libVLC：程序不模拟鼠标，不控制 PotPlayer，也不向 Windows 发送全局输入事件。

## 固件

构建固件：

```powershell
pio run
```

烧录到已连接的 M5StickC Plus2：

```powershell
pio run -t upload --upload-port COM5
```

固件会广播 BLE 设备名 `M5HeadTracker`，并以约 30 Hz 发送 JSON 遥测数据。

遥测特征 UUID：

```text
7d2f4b8a-6d0e-4f88-9e1f-0c8d2f5f5a02
```

## PC 端命令

运行测试：

```powershell
uv run --no-sync pytest
```

运行 BLE 遥测接收器：

```powershell
uv run --extra ble m5-telemetry --address <BLE_ADDRESS> --log logs/telemetry.jsonl
```

运行 tkinter 姿态可视化工具：

```powershell
uv run --extra ble m5-visualizer --address <BLE_ADDRESS>
```

运行 VLC 360 播放器 GUI：

```powershell
uv run --extra player m5-vlc-player
```

播放器本地配置读写路径：

```text
config/local.vlc-player.json
```

默认 VLC 目录为 `D:\Program Files\VideoLAN\VLC`。本机需要已安装 VLC 3.x。编解码能力由 VLC/libVLC 提供，本项目不安装编解码器，也不转码视频。

## 360 视频投影

很多本地 2:1 VR MP4 文件没有 spherical metadata。PotPlayer 可以通过菜单强制选择 `Equirectangular`，但 VLC 可能把它当普通平面视频。

播放器默认启用 `360 metadata`：程序会启动一个本地虚拟 MP4 Range server，把 Google equirectangular metadata 注入到内存头部，并把媒体数据映射回原始视频文件。这样 VLC 能收到带 360 metadata 的 MP4 流，同时不会生成第二份 5-7 GB 视频缓存。

## 校准与当前实测配置

当前实测可用配置保存在 `config/local.vlc-player.json`。关键字段如下：

```json
{
  "front_yaw_degrees": 90.0,
  "front_pitch_degrees": 0.0,
  "yaw_source_axis": "roll",
  "yaw_source_sign": 1.0,
  "pitch_source_axis": "yaw",
  "pitch_source_sign": -1.0
}
```

含义：

- `front_yaw_degrees = 90.0`：当 M5 正对屏幕并按下校准按钮时，VLC 视角不是看视频球面的 `0°`，而是看 `90°`。这与当前样片的画面中心对齐。
- `yaw_source_axis = roll`、`yaw_source_sign = 1.0`：眼镜上的 M5 实际佩戴姿态下，左右转头主要表现为传感器 `roll` 变化，所以左右视角控制使用 `roll`。
- `pitch_source_axis = yaw`、`pitch_source_sign = -1.0`：抬头/低头主要表现为传感器 `yaw` 变化，并且方向与播放器需要的方向相反，所以要反号。

推荐使用流程：

1. 启动 `m5-vlc-player`。
2. 打开 360 视频。
3. 点击 `连接 M5`。
4. 眼睛正对屏幕，让 M5 与屏幕保持约 90 度正对关系。
5. 按下 M5 主按钮，或点击 GUI 的 `校准`。
6. 如果左右或上下方向不对，使用 `学习左转` 和 `学习抬头` 自动识别轴映射。
7. 方向正确后点击 `保存配置`。

## 播放控制

播放器画面底部有悬浮控制条，包含：

- `-10s`：后退 10 秒。
- `播放`：开始或继续播放。
- `暂停`：暂停播放。
- `+10s`：快进 10 秒。
- 进度条：拖动后跳转到对应播放位置。
- 时间显示：当前时间 / 视频总时长。

键盘快捷键：

- `←`：后退 10 秒。
- `→`：快进 10 秒。

当焦点在文本输入框或下拉框里时，左右方向键优先用于编辑文本，不触发快进/后退。

## 调参说明

- `Yaw` / `Pitch`：左右和上下控制乘数，默认 `5.0`。`1.0` 表示传感器角度与画面角度一比一；`5.0` 表示传感器移动 `10°` 时，画面按 `50°` 处理。想要更敏感可以继续加大；如果太灵敏，可以退回 `2.0`、`1.5` 或 `1.0`。
- `Deadzone`：小抖动死区。值越大，越不容易响应细微晃动。
- `MaxYaw` / `MaxPitch`：头控最大偏转范围。左右最终画面被限制在 `0°..180°`；上下最终画面被限制在 `-MaxPitch..+MaxPitch`，避免放大后一下转到不可控区域。
- `Smooth`：平滑系数。值越小越稳，但响应更慢。
- `Step`：单次更新允许的最大角度跳变，防止突发数据导致画面猛跳。
- `FrontYaw` / `FrontPitch`：视频自身正前方偏移。校准能把头部姿态归零，但视频里“人物中心”不一定在 VLC 的 `0°`。

## v1 边界

v1 只交付 M5StickC Plus2 到 PC 的传感器数据链路，不控制 PotPlayer，不移动鼠标，不调用 Windows 窗口控制 API。可视化工具只是 PC 端诊断预览。

## v2 边界

v2 使用内嵌 VLC/libVLC 播放 360 视频，并通过 viewpoint API 控制视角。v2 不控制 PotPlayer，也不模拟鼠标或键盘输入。
