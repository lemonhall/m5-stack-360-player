# PRD-0002：M5 控制的 VLC 360 播放器

## 愿景

柠檬叔需要一个基本可用的 Windows 桌面 360 视频播放器：打开应用后可以从 GUI 选择媒体文件、播放/暂停，并用固定在眼镜上的 M5StickC Plus2 控制 VLC 的 360 视角。成功状态是：不模拟鼠标、不依赖 PotPlayer 前台窗口，而是通过 libVLC 的 viewpoint API 直接控制 360 视野。

## 背景

v1 已完成 M5StickC Plus2 到 PC 的 BLE 遥测链路和 tkinter 姿态可视化。PotPlayer 的 360 视角外部控制接口不可确认，稳定方案大概率只能靠鼠标拖拽模拟。VLC 3.x 支持 360 video viewpoint，且本机 `D:\Program Files\VideoLAN\VLC\libvlc.dll` 已验证导出 `libvlc_video_update_viewpoint`。本地 VR 片源按 PotPlayer 的 `Equirectangular` 菜单项播放；若原始 MP4 缺失 spherical metadata，应用会通过本地虚拟 MP4 URL 给 VLC 提供带 equirectangular metadata 的流，不生成 5-7 GB 缓存副本。[ECN-0002]

## 需求

### REQ-0002-001：优先提供 GUI 播放器入口

- **动机**：用户不应每次输入长命令和路径。
- **范围**：提供 `m5-vlc-player` 启动入口，启动后进入 tkinter GUI；媒体选择、BLE 连接、播放控制和配置保存均在 GUI 内完成。
- **非目标**：不要求打包成 `.exe` 安装器；不要求隐藏所有诊断日志。
- **验收口径**：`uv run --extra player m5-vlc-player --help` 能显示入口；GUI 类和控制器可被测试导入；用户命令不需要传 `--media` 或 `--address`。

### REQ-0002-002：本地可编辑配置

- **动机**：VLC 目录、BLE 地址、上次媒体和调参项应能持久化。
- **范围**：使用本地 JSON 配置 `config/local.vlc-player.json`；缺失时自动使用默认值；保存时自动创建目录；默认启用 `serve_spherical_metadata`。
- **非目标**：不提交用户本地配置；不做多用户配置同步。
- **验收口径**：单元测试覆盖缺失配置、保存配置、部分字段回退默认值；`.gitignore` 忽略 `config/local.*.json`。

### REQ-0002-003：内嵌 VLC 播放

- **动机**：播放器必须基本可用，不能只是控制探针。
- **范围**：tkinter 窗口内嵌 libVLC 视频输出；支持打开媒体文件、播放、暂停、停止。
- **非目标**：不实现播放列表、字幕库、转码、滤镜、网络串流管理。
- **验收口径**：VLC 绑定层能验证 `libvlc.dll`、`plugins` 和 `video_update_viewpoint` 可用；控制器测试覆盖 open/play/pause/stop 调用链；MP4 metadata 注入测试覆盖 spherical UUID、equirectangular XML 和 `stco/co64` 偏移修正。[ECN-0002]

### REQ-0002-004：M5 BLE 控制 VLC 视角

- **动机**：头部姿态应直接控制 360 视角。
- **范围**：复用 v1 BLE transport、telemetry parser 和 calibration；M5 主按钮或 GUI 校准按钮设置中心视角；相对 yaw/pitch/roll 转换为 VLC viewpoint。
- **非目标**：不控制 PotPlayer；不模拟鼠标；不发送 Windows 全局输入事件。
- **验收口径**：单元测试覆盖姿态到 viewpoint 的增益、死区、FOV 和 pitch clamp；生产代码扫描无 `SendInput`、`SetCursorPos`、`pyautogui`、PotPlayer 控制路径。

### REQ-0002-005：基础运行诊断

- **动机**：编解码器和 libVLC 问题对用户不可见时难排查。
- **范围**：GUI 状态栏显示 VLC 状态、媒体路径、BLE 状态、当前 viewpoint；启动时检查 VLC 路径和插件目录。
- **非目标**：不内置安装 VLC，不自动下载编解码器。
- **验收口径**：缺失 VLC 路径时状态给出明确错误；README 记录 VLC 3.x 和 codec 注意事项。

### REQ-0002-006：姿态控制灵敏度与最终视角限位

- **动机**：用户希望小幅转头即可产生更大的画面位移，同时避免视角越过可用范围后跳到视频接缝或不可控位置。
- **范围**：`Yaw` / `Pitch` 作为姿态角到画面角的乘数，默认值为 `5.0`；左右最终 VLC yaw 输出固定限制在 `0°..180°`；上下最终 VLC pitch 输出限制在 `-MaxPitch..+MaxPitch`。
- **非目标**：不改变校准逻辑；不改变左右 `0°..180°` 限位；不引入复杂曲线、非线性加速或自动灵敏度学习。
- **验收口径**：单元测试覆盖 `gain_yaw/gain_pitch=5.0` 时默认画面角位移放大 5 倍；测试覆盖放大后 yaw 仍被限制在 `0°..180°`，pitch 仍被限制在 `-MaxPitch..+MaxPitch`。
