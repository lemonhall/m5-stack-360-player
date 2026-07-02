# v3 计划：头控灵敏度与上下限位

## Goal

让用户可以通过 `Yaw` / `Pitch` 乘数用更小的头部动作控制更大的 360 画面位移，同时确保放大后的最终 VLC 视角仍被限位约束住。

## PRD Trace

- `REQ-0002-006`：姿态控制灵敏度与最终视角限位。

## Scope

做：

- 在 viewpoint 映射层支持配置化 pitch 最终输出范围。
- 控制器把 `MaxPitch` 传入 viewpoint 映射层。
- 把 `Yaw` / `Pitch` 默认乘数设为 `5.0`。
- 单元测试覆盖乘数放大和最终 yaw/pitch 限位。
- README 更新调参说明。

不做：

- 不改变校准逻辑。
- 不改变左右 `0°..180°` 的最终限位。
- 不改变 BLE 协议、固件或姿态平滑算法。
- 不加入非线性曲线或自动灵敏度学习。

## Acceptance

- `test_load_config_missing_file_returns_defaults` 证明缺失配置时 `gain_yaw/gain_pitch` 默认是 `5.0`。
- `test_map_ypr_to_viewpoint_applies_gain_before_configured_bounds` 证明 `gain_yaw/gain_pitch=2.0` 先放大位移，再按 yaw/pitch 最终范围限位。
- `test_controller_passes_configured_pitch_bounds_to_viewpoint_mapping` 证明 GUI 配置里的 `MaxPitch` 被传到最终 VLC viewpoint 映射层。
- `uv run --extra player pytest tests/test_vlc_viewpoint.py tests/test_vlc_player_controller.py -q` exit code 0。
- `uv run --extra player pytest -q` exit code 0。
- `pio run` exit code 0。
- `uv run --extra player m5-vlc-player --help` exit code 0。

## Files

- `pc_receiver/vlc_viewpoint.py`
- `pc_receiver/vlc_player_app.py`
- `tests/test_vlc_viewpoint.py`
- `tests/test_vlc_player_controller.py`
- `README.md`
- `docs/prd/PRD-0002-vlc-360-player.md`
- `docs/plan/v3-index.md`
- `docs/plan/v3-sensitivity-bounds.md`

## Steps

1. 写失败测试：补 viewpoint 和 controller 测试，先证明当前代码没有按 `MaxPitch` 做最终 pitch 限位。
2. 跑到红：运行 `uv run --extra player pytest tests/test_vlc_viewpoint.py tests/test_vlc_player_controller.py -q`，预期新增测试失败。
3. 实现到绿：给 `ViewpointSettings` 增加 pitch 最终范围，并从控制器传入 `-MaxPitch..+MaxPitch`。
4. 跑到绿：运行相关测试和全量测试。
5. 必要重构：只做局部命名或重复清理，保持测试绿。
6. E2E：运行 `uv run --extra player m5-vlc-player --help`；本轮不自动打开真实 5-7 GB 视频。
7. Review Loop：检查 PRD/plan/README/test/code 追溯和 diff，记录到 `v3-index.md`。
8. Ship：提交并推送一个 v3 commit，便于回滚。

## Risks

- 体感风险：默认 `5.0` 仍可能不够或过猛。缓解：README 说明可继续加大，或退回 `2.0` / `1.5` / `1.0`，并保留 `MaxPitch` 控制最终范围。
- 语义风险：`MaxPitch` 既在姿态控制层限制输入，又在 viewpoint 层限制最终输出。缓解：测试明确覆盖最终输出限位，README 写清它是最终上下范围保护。
