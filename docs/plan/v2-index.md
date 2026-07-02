# v2 Index: M5-Controlled VLC 360 Player

## Vision

见 [PRD-0002](../prd/PRD-0002-vlc-360-player.md)。v2 交付一个 GUI-first 的 VLC 360 播放器，用 M5StickC Plus2 姿态通过 libVLC viewpoint API 控制视角。

## Version Scope

v2 做：

- tkinter GUI 播放器窗口。
- GUI 内打开媒体文件、播放、暂停、停止。
- 本地 JSON 配置，默认 VLC 路径 `D:\Program Files\VideoLAN\VLC`，默认 BLE 地址 `0C:8B:95:B4:7B:5A`。
- 嵌入 libVLC 播放视频，并检查 VLC 目录、插件目录和 viewpoint API。
- 复用 v1 BLE 遥测链路和校准逻辑，把 M5 姿态映射到 VLC viewpoint。

v2 不做：

- 不控制 PotPlayer。
- 不模拟鼠标、键盘或 Windows 全局输入。
- 不做 VLC 安装器，不自动下载编解码器。
- 不做播放列表、字幕管理、媒体库或网络串流管理。

## Milestones

| Milestone | Scope | DoD | Verification | Status |
|---|---|---|---|---|
| M1 | PRD/ECN/v2 plan | PRD-0002、ECN-0001、v2-index、v2-vlc-player 存在且有追溯矩阵 | `rg "REQ-0002" docs/prd docs/plan`; doc mojibake scan | done |
| M2 | Config + viewpoint core | 配置读写、VLC 路径验证、姿态到 viewpoint 映射可测试 | `python -m pytest tests/test_vlc_player_config.py tests/test_vlc_viewpoint.py` | done |
| M3 | VLC GUI player shell | `m5-vlc-player` GUI 入口、打开媒体、播放/暂停/停止控制器可测试 | `python -m pytest tests/test_vlc_player_controller.py tests/test_python_runtime_policy.py`; `uv run --extra player m5-vlc-player --help` | done |
| M4 | BLE to VLC viewpoint integration | BLE snapshot 能更新 viewpoint；生产路径无 PotPlayer/鼠标模拟 | `python -m pytest`; production scan; libVLC probe; GUI smoke | done |

## Plan Index

- [v2-vlc-player.md](v2-vlc-player.md)

## Traceability Matrix

| Req ID | PRD | v2 Plan | Unit/Integration | E2E/Hardware | Evidence | Status |
|---|---|---|---|---|---|---|
| REQ-0002-001 | PRD-0002 | v2-vlc-player M3 | script metadata + import tests | `uv run --extra player m5-vlc-player --help` | help exits 0 | done |
| REQ-0002-002 | PRD-0002 | v2-vlc-player M2 | config load/save tests | app starts with defaults | `tests/test_vlc_player_config.py` passed | done |
| REQ-0002-003 | PRD-0002 | v2-vlc-player M3 | fake VLC controller tests | manual GUI open media | `tests/test_vlc_player_controller.py` passed | done |
| REQ-0002-004 | PRD-0002 | v2-vlc-player M4 | viewpoint mapper tests | BLE-to-viewpoint integration test | `tests/test_vlc_viewpoint.py` and controller relative-ypr test passed; libVLC probe passed | done |
| REQ-0002-005 | PRD-0002 | v2-vlc-player M2/M3 | VLC validation tests | status/error display path | `validate_vlc_dir` tests passed; README documents codecs | done |

## ECN Index

- [ECN-0001](../ecn/ECN-0001-potplayer-to-vlc-player.md): Replace PotPlayer target with embedded VLC player.

## DoD Hardness Gate

- `python -m pytest` exits 0.
- `uv run --extra player m5-vlc-player --help` exits 0.
- VLC probe verifies `D:\Program Files\VideoLAN\VLC\libvlc.dll` loads and exports `libvlc_video_update_viewpoint`.
- Production scan over `pc_receiver pyproject.toml` has no `SendInput`, `SetCursorPos`, `pyautogui`, `PotPlayer` control implementation.
- `.gitignore` ignores `config/local.*.json`.
- README documents VLC 3.x requirement and codec responsibility.

## Doc QA Gate

- Every PRD-0002 requirement is present in the traceability matrix.
- Every milestone has a binary verification command or explicit manual hardware note.
- ECN-0001 is linked from this index.
- Scope explicitly excludes PotPlayer and global input simulation.

## Tashan Trigger Audit

- expected_review_triggers: v2 doc writing, M2/M3/M4 completion, final v2 ship.
- actual_review_runs: 0
- skipped_triggers: 0
- skip_reasons: none
- mitigation: record review before final completion signal.

## Difference List

- v2 live video playback with an actual 360 file may require a user-selected media sample; automated tests will cover control contracts and libVLC API availability.

## Implementation Evidence - 2026-07-02

- Final `python -m pytest`: 37 passed.
- `uv run --extra player m5-vlc-player --help`: exit 0.
- Local libVLC probe: `probe_vlc_viewpoint_api(r'D:\Program Files\VideoLAN\VLC')` returned `True`.
- `python-vlc` 3.0.21203 exposes `VideoViewpoint` and `MediaPlayer.video_update_viewpoint`.
- `.gitignore` ignores `config/local.*.json`.
- GUI smoke: `m5-vlc-player --config config/local.vlc-player-smoke.json` stayed alive for 4 seconds and was stopped.
- Production scan over `pc_receiver pyproject.toml` found no `SendInput`, `SetCursorPos`, `pyautogui`, `PotPlayer`, or `mouse_event` control path.

## Tashan Review - v2 / VLC Player

- reviewer_context: same-model
- round: 1
- cost_profile: standard
- verdict: pass
- blocker_count: 0
- major_count: 0
- stuck_signatures: none
- regression_signatures: none
- commands_checked: `python -m pytest`; `uv run --extra player m5-vlc-player --help`; libVLC viewpoint probe; GUI smoke; production forbidden-control scan; mojibake/NUL scan
- residual_risks: actual 360 media playback quality depends on VLC codec support and the user-selected media file; live BLE-to-VLC visual behavior still benefits from a real video sample and human tuning.

### Findings

| severity | signature | evidence | disposition |
|---|---|---|---|
| NOTE | codec::vlc::media-dependent | VLC/libVLC owns codec support; app does not bundle codecs | documented in README |
| NOTE | live-tuning::viewpoint::gain-deadzone | Gain/FOV/deadzone defaults are conservative and may need user tuning with a real 360 file | exposed in GUI config fields |
