# ECN-0002：为 VLC 注入 Equirectangular 元数据

## 基本信息

- **ECN 编号**：ECN-0002
- **关联 PRD**：PRD-0002
- **关联 Req ID**：REQ-0002-002、REQ-0002-003、REQ-0002-004
- **发现阶段**：v2 真实媒体校验
- **日期**：2026-07-02

## 变更原因

真实本地 VR 文件是 2:1 HEVC MP4。PotPlayer 在 360 菜单设置为 `Equirectangular` 后可以正确播放。`ffprobe` 显示样片没有携带 spherical metadata，因此 VLC 自动检测时可能把画面当作普通平面视频渲染，除非强制声明投影方式。

此前认为这需要放弃 VLC 的判断是错误的。目标仍然是内嵌 VLC/libVLC。

## 变更内容

### 原设计

允许 VLC 自动检测媒体文件是否应使用 360 投影。

### 被替代设计

第一版实现会创建或复用一份带 Google spherical metadata 的 MP4 缓存副本，用于声明 equirectangular 投影。但目标媒体通常是 5-7 GB，这种方式不可接受。

### 当前设计

VLC 播放器提供一个本地虚拟 MP4 URL。虚拟文件在内存头部注入 Google equirectangular metadata，并通过 HTTP Range 读取把媒体数据映射回原始文件。这样既避免生成第二份 5-7 GB 视频文件，也能让 VLC 收到带 metadata 的 MP4 流。

## 影响范围

- 受影响 Req ID：REQ-0002-002、REQ-0002-003、REQ-0002-004
- 受影响 v2 计划：`docs/plan/v2-index.md`、`docs/plan/v2-vlc-player.md`
- 受影响测试：`tests/test_virtual_mp4_server.py`、`tests/test_mp4_spherical_metadata.py`、`tests/test_vlc_player_config.py`、`tests/test_vlc_player_controller.py`
- 受影响代码：`pc_receiver/virtual_mp4_server.py`、`pc_receiver/mp4_spherical_metadata.py`、`pc_receiver/vlc_player_config.py`、`pc_receiver/vlc_player_app.py`

## 处置状态

- [x] PRD 已更新
- [x] v2 计划已更新
- [x] 测试已更新
- [x] README 已更新
