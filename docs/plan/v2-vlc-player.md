# v2 计划：VLC 播放器

## 目标

交付 PRD-0002：一个 GUI 优先的 VLC 360 播放器，通过 libVLC viewpoint API 接收 M5StickC Plus2 BLE 遥测并控制视角。

## PRD 追溯

- REQ-0002-001：GUI 优先的播放器启动入口
- REQ-0002-002：本地可编辑配置
- REQ-0002-003：内嵌 VLC 播放
- REQ-0002-004：M5 BLE 视角控制
- REQ-0002-005：基础运行诊断

## 范围

做：

- 添加 `player` 可选依赖组，包含 `bleak` 和 `python-vlc`。
- 添加本地 JSON 配置读写。
- 添加 VLC 绑定/适配层和 viewpoint 映射器。
- 为 VLC 播放提供本地虚拟 MP4 URL，注入 equirectangular spherical metadata，且不复制 5-7 GB 媒体文件。
- 添加 tkinter GUI 播放器，支持打开媒体、播放/暂停/停止、连接 BLE、校准、保存配置。
- 添加配置、viewpoint 映射、控制器、脚本元数据、无鼠标控制回归测试。

不做：

- 不控制 PotPlayer。
- 不模拟鼠标或键盘。
- 不安装 VLC 或编解码器。
- 不构建 `.exe` 安装器。

## 验收

- `python -m pytest` 通过。
- `uv run --extra player m5-vlc-player --help` exit code 0。
- `python -c` VLC 探针能加载本地 `libvlc.dll` 并确认 `libvlc_video_update_viewpoint`。
- 虚拟 MP4 测试证明 spherical UUID 注入、equirectangular XML、Range serving 和 chunk offset 修复。
- `rg -n "SendInput|SetCursorPos|pyautogui|PotPlayer" pc_receiver pyproject.toml` 没有生产控制路径命中。
- `config/local.vlc-player.json` 被 git 忽略，只在运行时创建。

## 文件

- 创建 `pc_receiver/vlc_player_config.py`
- 创建 `pc_receiver/vlc_viewpoint.py`
- 创建 `pc_receiver/vlc_backend.py`
- 创建 `pc_receiver/vlc_player_app.py`
- 创建 `tests/test_vlc_player_config.py`
- 创建 `tests/test_vlc_viewpoint.py`
- 创建 `tests/test_vlc_player_controller.py`
- 修改 `pyproject.toml`
- 修改 `.gitignore`
- 修改 `README.md`
- 修改 `docs/plan/v2-index.md`

## 步骤

1. 红灯：写配置和 viewpoint 映射测试。
2. 绿灯：实现配置和 viewpoint 映射器。
3. 红灯：用 fake VLC 写适配器/控制器测试。
4. 绿灯：实现 VLC backend 抽象和控制器。
5. 红灯：添加虚拟 MP4 Range server、metadata 和配置测试。
6. 绿灯：默认提供虚拟 spherical metadata URL，并暴露配置勾选项。
7. 红灯：扩展 `m5-vlc-player` 脚本元数据测试。
8. 绿灯：实现 tkinter 应用外壳和脚本入口。
9. E2E：运行全量测试、`m5-vlc-player --help`、本地 libVLC 探针和真实样片人工视觉检查。
10. 评审循环：验证追溯、无 PotPlayer/鼠标控制路径、文档已更新、无乱码。
11. 交付：所有阻塞关闭后再 commit、push、发送完成通知。

## 风险

- **编解码/媒体兼容性**：VLC 负责解码；应用必须暴露 VLC 错误，但不捆绑编解码器。
- **Windows 上的 Tk/VLC 嵌入**：使用 `Frame.winfo_id()` 和 `MediaPlayer.set_hwnd`。
- **python-vlc 加载路径**：导入 `vlc` 前设置 `PYTHON_VLC_LIB_PATH`、`VLC_PLUGIN_PATH` 和 `os.add_dll_directory(vlc_dir)`。
- **BLE/live 依赖**：复用 v1 的 Python 3.13 pin 和 `bleak` 依赖。
