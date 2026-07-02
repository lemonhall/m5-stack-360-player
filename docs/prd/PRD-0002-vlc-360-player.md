# PRD-0002: M5-Controlled VLC 360 Player

## Vision

柠檬叔需要一个基本可用的 Windows 桌面 360 视频播放器：打开应用后可以从 GUI 选择媒体文件、播放/暂停，并用固定在眼镜上的 M5StickC Plus2 控制 VLC 的 360 视角。成功状态是：不模拟鼠标、不依赖 PotPlayer 前台窗口，而是通过 libVLC 的 viewpoint API 直接控制 360 视野。

## Context

v1 已完成 M5StickC Plus2 到 PC 的 BLE 遥测链路和 tkinter 姿态可视化。PotPlayer 的 360 视角外部控制接口不可确认，稳定方案大概率只能靠鼠标拖拽模拟。VLC 3.x 支持 360 video viewpoint，且本机 `D:\Program Files\VideoLAN\VLC\libvlc.dll` 已验证导出 `libvlc_video_update_viewpoint`。本地 VR 片源按 PotPlayer 的 `Equirectangular` 菜单项播放；若原始 MP4 缺失 spherical metadata，应用会通过本地虚拟 MP4 URL 给 VLC 提供带 equirectangular metadata 的流，不生成 5-7 GB 缓存副本。[ECN-0002]

## Requirements

### REQ-0002-001: GUI-first player launch

- **Motivation**: 用户不应每次输入长命令和路径。
- **Scope**: 提供 `m5-vlc-player` 启动入口，启动后进入 tkinter GUI；媒体选择、BLE 连接、播放控制和配置保存均在 GUI 内完成。
- **Non-goals**: 不要求打包成 `.exe` 安装器；不要求隐藏所有诊断日志。
- **Acceptance**: `uv run --extra player m5-vlc-player --help` 能显示入口；GUI 类和控制器可被测试导入；用户命令不需要传 `--media` 或 `--address`。

### REQ-0002-002: Local editable config

- **Motivation**: VLC 目录、BLE 地址、上次媒体和调参项应能持久化。
- **Scope**: 使用本地 JSON 配置 `config/local.vlc-player.json`；缺失时自动使用默认值；保存时自动创建目录；默认启用 `serve_spherical_metadata`。
- **Non-goals**: 不提交用户本地配置；不做多用户配置同步。
- **Acceptance**: 单元测试覆盖缺失配置、保存配置、部分字段回退默认值；`.gitignore` 忽略 `config/local.*.json`。

### REQ-0002-003: Embedded VLC playback

- **Motivation**: 播放器必须基本可用，不能只是控制探针。
- **Scope**: tkinter 窗口内嵌 libVLC 视频输出；支持打开媒体文件、播放、暂停、停止。
- **Non-goals**: 不实现播放列表、字幕库、转码、滤镜、网络串流管理。
- **Acceptance**: VLC 绑定层能验证 `libvlc.dll`、`plugins` 和 `video_update_viewpoint` 可用；控制器测试覆盖 open/play/pause/stop 调用链；MP4 metadata 注入测试覆盖 spherical UUID、equirectangular XML 和 `stco/co64` 偏移修正。[ECN-0002]

### REQ-0002-004: M5 BLE viewpoint control

- **Motivation**: 头部姿态应直接控制 360 视角。
- **Scope**: 复用 v1 BLE transport、telemetry parser 和 calibration；M5 主按钮或 GUI 校准按钮设置中心视角；相对 yaw/pitch/roll 转换为 VLC viewpoint。
- **Non-goals**: 不控制 PotPlayer；不模拟鼠标；不发送 Windows 全局输入事件。
- **Acceptance**: 单元测试覆盖姿态到 viewpoint 的增益、死区、FOV 和 pitch clamp；生产代码扫描无 `SendInput`、`SetCursorPos`、`pyautogui`、PotPlayer 控制路径。

### REQ-0002-005: Basic operational diagnostics

- **Motivation**: 编解码器和 libVLC 问题对用户不可见时难排查。
- **Scope**: GUI 状态栏显示 VLC 状态、媒体路径、BLE 状态、当前 viewpoint；启动时检查 VLC 路径和插件目录。
- **Non-goals**: 不内置安装 VLC，不自动下载编解码器。
- **Acceptance**: 缺失 VLC 路径时状态给出明确错误；README 记录 VLC 3.x 和 codec 注意事项。
