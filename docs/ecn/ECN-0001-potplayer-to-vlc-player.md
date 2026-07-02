# ECN-0001: Replace PotPlayer Target With Embedded VLC Player

## Basic Information

- **ECN 编号**: ECN-0001
- **关联 PRD**: PRD-0001, PRD-0002
- **关联 Req ID**: REQ-0002-003, REQ-0002-004
- **发现阶段**: v2 design
- **日期**: 2026-07-02

## Change Reason

原始方向是后续控制 PotPlayer 360 VR 视角。但调研后没有确认到稳定的 PotPlayer 360 viewpoint 外部 API，实际可行路径偏向鼠标拖拽模拟，误操作风险高，且难以测试。

VLC 3.x 官方支持 360 video viewpoint，libVLC 暴露 `libvlc_video_update_viewpoint`。本机 VLC 3.0.23 位于 `D:\Program Files\VideoLAN\VLC`，已验证 `libvlc.dll` 可加载且导出 viewpoint API。

## Change Content

### Original Design

后续控制 PotPlayer 的 360 模式视角。

### New Design

v2 不控制 PotPlayer。v2 构建一个 tkinter GUI VLC 360 播放器，嵌入 libVLC 播放视频，并用 M5 BLE 姿态直接调用 VLC viewpoint API。

## Impact Scope

- 受影响的 Req ID: 新增 PRD-0002 的 REQ-0002-001 到 REQ-0002-005
- 受影响的 vN 计划: 新增 `docs/plan/v2-index.md` 和 `docs/plan/v2-vlc-player.md`
- 受影响的测试: 新增 config、VLC adapter、viewpoint mapper、player controller 测试
- 受影响的代码文件: `pc_receiver/vlc_player_*.py`、`pyproject.toml`、`.gitignore`

## Disposition

- [x] PRD 已同步新增 PRD-0002
- [x] v2 计划将同步更新
- [x] 追溯矩阵将同步更新
- [x] 相关测试将在 v2 实现中新增

