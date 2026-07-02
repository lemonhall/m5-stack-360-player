# v3 索引：头控灵敏度与上下限位

## 愿景

见 [PRD-0002](../prd/PRD-0002-vlc-360-player.md)。v3 只处理头控体感调参：用户可以用 `Yaw` / `Pitch` 乘数放大传感器角度对应的画面位移，同时左右和上下最终视角都有硬限位，避免越界后跳到视频接缝或不可控区域。

## 版本范围

v3 做：

- 明确 `Yaw` / `Pitch` 是姿态角到画面角的乘数，并把默认值设为 `5.0`。
- 保持左右最终 VLC yaw 输出限制在 `0°..180°`。
- 新增上下最终 VLC pitch 输出限制为 `-MaxPitch..+MaxPitch`。
- 更新测试和 README，让调参方式可回归、可理解。

v3 不做：

- 不改变校准按钮、M5 主按钮或中心姿态逻辑。
- 不改变左右 `0°..180°` 的限位器逻辑。
- 不引入非线性曲线、自动学习灵敏度或播放器 UI 大改。
- 不改 BLE 协议和固件。

## 里程碑

| 里程碑 | 范围 | 完成定义 | 验证 | 状态 |
|---|---|---|---|---|
| M1 | PRD/plan | REQ-0002-006、v3-index、v3-sensitivity-bounds 存在并可追溯 | `rg "REQ-0002-006" docs/prd docs/plan`; mojibake scan | done |
| M2 | Viewpoint 映射 | `Yaw/Pitch` 乘数放大后仍受最终 yaw/pitch 限位约束 | `uv run --extra player pytest tests/test_vlc_player_config.py tests/test_vlc_viewpoint.py tests/test_vlc_player_controller.py -q` | done |
| M3 | 文档与整体验证 | README 写清乘数与限位；全量测试和固件构建通过 | `uv run --extra player pytest -q`; `pio run`; `uv run --extra player m5-vlc-player --help` | done |

## 计划索引

- [v3-sensitivity-bounds.md](v3-sensitivity-bounds.md)

## 追溯矩阵

| Req ID | PRD | v3 计划 | 单元/集成 | E2E/硬件 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| REQ-0002-006 | PRD-0002 | v3-sensitivity-bounds M2/M3 | `tests/test_vlc_player_config.py`; `tests/test_vlc_viewpoint.py`; `tests/test_vlc_player_controller.py` | GUI help + 用户实机体感测试 | automated checks passed; user-side feel test pending | done |

## ECN 索引

- 本轮没有 ECN。v3 是新增调参需求，不改变既有 PRD 设计口径。

## DoD 硬门禁

- `uv run --extra player pytest tests/test_vlc_player_config.py tests/test_vlc_viewpoint.py tests/test_vlc_player_controller.py -q` exit code 0，且包含 `gain_yaw/gain_pitch=5.0` 默认值与 pitch 最终限位断言。
- `uv run --extra player pytest -q` exit code 0。
- `pio run` exit code 0。
- `uv run --extra player m5-vlc-player --help` exit code 0。
- README 明确写出：`Yaw/Pitch` 是乘数，默认 `5.0`；`MaxPitch` 是最终上下输出限位。
- 反作弊条款：不得只改 README 或默认值；必须有测试证明乘数先放大、最终限位后生效。

## 文档 QA 门禁

- PRD-0002 存在 `REQ-0002-006`，并写清范围、非目标、验收口径。
- v3 追溯矩阵包含 `REQ-0002-006`。
- v3 DoD 每条都有可重复命令或明确人工验收说明。
- 范围明确排除校准逻辑、BLE 协议和固件改动。

## 塔山触发审计

- expected_review_triggers: v3 doc writing, M2/M3 completion, final v3 ship.
- actual_review_runs: 1
- skipped_triggers: 0
- skip_reasons: none
- mitigation: review recorded before final ship.

## 差异列表

- 用户最终体感仍需要实机佩戴测试确认；本轮自动化只能证明数学映射、限位和入口命令正确。

## 实现证据 - 2026-07-03

- TDD Red：`uv run --extra player pytest tests/test_vlc_player_config.py -q` 先失败，证明默认值仍是 `2.0`。
- 相关测试：`uv run --extra player pytest tests/test_vlc_player_config.py tests/test_vlc_viewpoint.py tests/test_vlc_player_controller.py -q`，28 passed。
- 全量测试：`uv run --extra player pytest -q`，70 passed。
- 固件构建：`pio run`，SUCCESS。
- 播放器入口：`uv run --extra player m5-vlc-player --help`，exit code 0。
- 本机 local 配置：`config/local.vlc-player.json` 的 `gain_yaw` 和 `gain_pitch` 已更新为 `5.0`。

## 塔山评审 - v3 / 头控灵敏度与上下限位

- reviewer_context: same-model
- round: 1
- cost_profile: light
- verdict: pass
- blocker_count: 0
- major_count: 0
- stuck_signatures: none
- regression_signatures: none
- commands_checked: `uv run --extra player pytest -q`; `pio run`; `uv run --extra player m5-vlc-player --help`; `git diff --check`; mojibake/NUL scan
- residual_risks: 用户最终体感需要在真实佩戴和真实 VR 文件里确认；自动化只能验证数学映射、限位、默认配置和入口命令。

### 发现项

| 严重级别 | 特征 | 证据 | 处置 |
|---|---|---|---|
| NOTE | live-tuning::gain-default::user-feel | 默认乘数改为 `5.0`，但不同片源和佩戴角度可能仍需调整 | README 记录可继续加大或退回 `2.0` / `1.5` / `1.0` |
