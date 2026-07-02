# v1 Index: M5StickC Plus2 Sensor Link

## Vision

见 [PRD-0001](../prd/PRD-0001-m5stickc-plus2-head-tracker.md)。v1 只交付 M5StickC Plus2 到 PC 的传感器数据链路，不控制 PotPlayer。

## Version Scope

v1 做：

- 从 M5StickC Plus2 官方 IMU/cube 示例建立固件基线。
- 保留 M5 屏幕上的 cube 或等价官方姿态可视化。
- 通过 BLE GATT 通知发送 JSON 遥测包。
- PC 端用 Python 接收、解析、实时显示、写 JSONL 日志。
- PC 端处理 M5 主按钮事件，把当前姿态设为中心姿态。
- PC 端提供 tkinter 诊断可视化窗口，把姿态显示为 3D 小棒。

v1 不做：

- 不控制 PotPlayer。
- 不模拟鼠标拖拽。
- 不把诊断可视化升级为 PotPlayer 控制或鼠标控制。
- 不把第一版协议做成二进制包。

## Milestones

| Milestone | Scope | DoD | Verification | Status |
|---|---|---|---|---|
| M1 | 找到并导入官方 IMU/cube 示例 | 有来源记录；工程能构建；屏幕可视化入口保留 | `docs/hardware/m5stickc-plus2-example-source.md` 存在；`pio run` exit code 0 | done |
| M2 | 固件 BLE JSON 遥测 | 遥测包含 `seq/ms/acc/gyro/btn` 和 `ypr` 或 `quat`；默认频率约 30 Hz 且可配置 | `uv run --no-sync pytest tests/test_firmware_static.py` 7 passed；串口 JSON 样例可解析 | done |
| M3 | PC 接收、显示、日志、校准 | PC 程序能接收模拟或真实遥测；按钮事件更新中心姿态；JSONL 每行可解析 | `uv run --no-sync pytest` 19 passed；模拟 BLE flow 通过 | done |
| M4 | 真实 M5 硬件链路验收 | M5 屏幕可视化正常；PC 通过 BLE 收包；按主按钮后相对姿态归零附近 | 固件已上传 COM5；串口 JSON 已验证；真实 BLE GATT 接收已验证 | partial |

## Plan Index

- [v1-sensor-link.md](v1-sensor-link.md)

## Traceability Matrix

| Req ID | PRD | v1 Plan | Unit/Integration | E2E/Hardware | Evidence | Status |
|---|---|---|---|---|---|---|
| REQ-0001-001 | PRD-0001 | v1-sensor-link M1 | 构建检查 | COM5 上传 | official source doc + `pio run` success | done |
| REQ-0001-002 | PRD-0001 | v1-sensor-link M2 | 遥测字段测试 | COM5 serial JSON | 10 JSON lines captured from COM5 | done |
| REQ-0001-003 | PRD-0001 | v1-sensor-link M2/M3 | BLE adapter boundary | BLE GATT live | `uv run --extra ble m5-telemetry --address 0C:8B:95:B4:7B:5A --max-packets 3` received 3 packets | done |
| REQ-0001-004 | PRD-0001 | v1-sensor-link M2/M3 | JSON parser 测试 | M3 模拟 E2E | `uv run --no-sync pytest` 19 passed | done |
| REQ-0001-005 | PRD-0001 | v1-sensor-link M2 | 频率配置测试 | serial interval sample | `TELEMETRY_HZ = 30`; serial `ms` increments around 36 ms | done |
| REQ-0001-006 | PRD-0001 | v1-sensor-link M3 | 校准状态测试 | M4 主按钮验收 | unit tests pass; real button BLE event not verified | partial |
| REQ-0001-007 | PRD-0001 | v1-sensor-link M3 | JSONL writer 测试 | M3 模拟 E2E | JSONL writer + simulated flow tests pass | done |
| REQ-0001-008 | PRD-0001 | v1-sensor-link M3/M4 | PotPlayer 禁入扫描 | production path scan | production path scan no hits | done |
| REQ-0001-009 | PRD-0001 | tk-visualizer add-on | 3D projection tests | PC diagnostic visualizer | `python -m pytest tests\test_visualization.py`; `uv run --extra ble m5-visualizer --help` | done |

## ECN Index

暂无。

## DoD Hardness Gate

- 每个里程碑都有可重复验证命令或硬件验收记录。
- M3 必须有自动化测试，不能只靠手动连接。
- M4 必须留下真实 JSONL 样例或验收日志。
- 反作弊条款：v1 代码中不得出现 PotPlayer 控制、鼠标拖拽或 Windows 窗口控制逻辑；必须用搜索命令验证。

## Doc QA Gate

- PRD 中每条需求都有 Req ID、范围、非目标、验收口径。
- v1 追溯矩阵每条 Req ID 都指向 v1 计划。
- 所有验收项均有命令、测试或硬件证据路径。
- 术语统一使用 M5、PC、遥测包、中心姿态、相对姿态。

## Review Loop

文档写作阶段 Review 记录：

- reviewer_context: same-model
- round: 1
- cost_profile: light
- verdict: pass
- blocker_count: 0
- major_count: 0
- stuck_signatures: none
- regression_signatures: none
- commands_checked: `rg --files`; `git diff --text -- docs`; suspicious mojibake/NUL scan over `docs`
- residual_risks: 当前目录初始不是 git 仓库；若无远程，文档提交只能本地 commit，push 需要后续配置 remote。

### Findings

| severity | signature | evidence | disposition |
|---|---|---|---|
| NOTE | git::repository::no-remote-yet | 初始 `git status` 报 not a git repository | 文档阶段会初始化本地 git；无 remote 时在 Ship 记录 |

## Tashan Trigger Audit

- expected_review_triggers: v1 文档写作完成前触发 Doc QA 和 Review Loop。
- actual_review_runs: 1
- skipped_triggers: 0
- skip_reasons: none
- mitigation: 后续实现里程碑按 M1-M4 分别触发 Review Loop。

## Difference List

- v1 尚未执行实现，证据列为 pending 属于计划状态，不构成文档阶段断链。
- 官方示例源码位置尚未确认，归入 M1。

## Ship Record

- local_commit: `82e9264` implementation branch commit, merged as `7acb79d`
- push_status: pushed
- push_note: `git push origin master` succeeded on 2026-07-02.

## Implementation Evidence - 2026-07-02

- `uv run --no-sync pytest`: 19 passed.
- `pio run`: success, firmware size RAM 13.0%, Flash 97.8%.
- `pio run -t upload --upload-port COM5`: success; device chip `ESP32-PICO-V3-02`, MAC `0c:8b:95:b4:7b:58`.
- COM5 serial sample after upload emitted JSON with `seq/ms/ypr/acc/gyro/btn`.
- `rg` suspicious mojibake/NUL scan: no hits after removing self-matching command text.
- Production path PotPlayer/control scan over `pc_receiver firmware platformio.ini pyproject.toml`: no hits.
- BLE live dependency check initially timed out because uv selected Python 3.14 for `.venv`, which caused Windows BLE `winrt-*` dependencies to enter build paths. Pinning project runtime to Python 3.13 fixed dependency installation.
- BLE live receive verified with `M5HeadTracker` at `0C:8B:95:B4:7B:5A`; `uv run --extra ble m5-telemetry --address 0C:8B:95:B4:7B:5A --log logs\ble-live-uv-3.jsonl --max-packets 3` received packets `seq=64394..64396`.
- PC diagnostic visualizer added as `m5-visualizer`; geometry covered by `tests\test_visualization.py`; command help verified with `uv run --extra ble m5-visualizer --help`.

## Tashan Review - v1 / Implementation

- reviewer_context: same-model
- round: 1
- cost_profile: standard
- verdict: pass-with-followup
- blocker_count: 0
- major_count: 0
- stuck_signatures: none
- regression_signatures: none
- commands_checked: `uv run --no-sync pytest`; `pio run`; `pio run -t upload --upload-port COM5`; serial COM5 read; production path control scan; mojibake scan
- residual_risks: real button-center BLE event still needs an explicit press test; PotPlayer control remains out of v1 scope.

### Findings

| severity | signature | evidence | disposition |
|---|---|---|---|
| RESOLVED | ble-live::REQ-0001-003::python-314-winrt-build-path | `uv run --extra ble` initially selected Python 3.14 and blocked while building `winrt-*`; Python 3.13 pin installed wheels and live BLE receive succeeded | fixed by `.python-version`, `requires-python`, and package metadata |
| NOTE | firmware::button-update::m5-update-crash | serial captured Guru Meditation at `main.cpp:144`; addr2line mapped crash to `StickCP2.update()` | fixed by raw GPIO37 edge read and regression static test |
