# v2 VLC Player Plan

## Goal

Deliver PRD-0002: a GUI-first VLC 360 player controlled by M5StickC Plus2 BLE telemetry through libVLC viewpoint APIs.

## PRD Trace

- REQ-0002-001: GUI-first player launch
- REQ-0002-002: Local editable config
- REQ-0002-003: Embedded VLC playback
- REQ-0002-004: M5 BLE viewpoint control
- REQ-0002-005: Basic operational diagnostics

## Scope

Do:

- Add `player` optional dependency group containing `bleak` and `python-vlc`.
- Add local JSON config loader/saver.
- Add VLC binding/adapter and viewpoint mapper.
- Serve a local virtual MP4 URL with equirectangular spherical metadata for VLC playback without copying 5-7 GB media files.
- Add tkinter GUI player with open media, play/pause/stop, connect BLE, calibrate, save config.
- Add tests for config, viewpoint mapping, controller behavior, script metadata, and no mouse-control regression.

Do not:

- Do not control PotPlayer.
- Do not simulate mouse or keyboard.
- Do not install VLC or codecs.
- Do not build an executable installer.

## Acceptance

- `python -m pytest` passes.
- `uv run --extra player m5-vlc-player --help` exits 0.
- `python -c` VLC probe loads local `libvlc.dll` and confirms `libvlc_video_update_viewpoint`.
- Virtual MP4 tests prove spherical UUID injection, equirectangular XML, Range serving, and chunk offset repair.
- `rg -n "SendInput|SetCursorPos|pyautogui|PotPlayer" pc_receiver pyproject.toml` has no production-control hits.
- `config/local.vlc-player.json` is ignored by git and created only at runtime.

## Files

- Create `pc_receiver/vlc_player_config.py`
- Create `pc_receiver/vlc_viewpoint.py`
- Create `pc_receiver/vlc_backend.py`
- Create `pc_receiver/vlc_player_app.py`
- Create `tests/test_vlc_player_config.py`
- Create `tests/test_vlc_viewpoint.py`
- Create `tests/test_vlc_player_controller.py`
- Modify `pyproject.toml`
- Modify `.gitignore`
- Modify `README.md`
- Modify `docs/plan/v2-index.md`

## Steps

1. Red: write config and viewpoint mapper tests.
2. Green: implement config and viewpoint mapper.
3. Red: write VLC adapter/controller tests with fakes.
4. Green: implement VLC backend abstraction and controller.
5. Red: add virtual MP4 Range server, metadata, and config tests for Equirectangular playback.
6. Green: serve virtual spherical metadata URL by default and expose the config checkbox.
7. Red: extend script metadata tests for `m5-vlc-player`.
8. Green: implement tkinter app shell and script entry.
9. E2E: run full tests, `m5-vlc-player --help`, local libVLC probe, and human visual check on the real sample.
10. Review Loop: verify traceability, no PotPlayer/mouse-control path, docs updated, no mojibake.
11. Ship: commit, push, send completion notification only when all blockers are closed.

## Risks

- **Codec/media compatibility**: VLC handles codecs; app must surface VLC errors but does not bundle codecs.
- **Tk/VLC embedding on Windows**: use `Frame.winfo_id()` with `MediaPlayer.set_hwnd`.
- **python-vlc load path**: set `PYTHON_VLC_LIB_PATH`, `VLC_PLUGIN_PATH`, and `os.add_dll_directory(vlc_dir)` before importing `vlc`.
- **BLE/live dependency**: reuse v1 Python 3.13 pin and `bleak` dependency.
