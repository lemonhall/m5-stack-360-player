# M5StickC Plus2 Sensor Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build v1 sensor link: M5StickC Plus2 sends JSON IMU telemetry over BLE, and the Windows PC receiver parses, displays, logs, and calibrates it.

**Architecture:** PC code is a small Python package with parser, calibration state, JSONL recorder, BLE transport, and CLI modules. Firmware is a PlatformIO Arduino project based on official M5StickCPlus2 IMU APIs, with telemetry construction separated from BLE notification and display code.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `bleak`, PlatformIO, Arduino ESP32, M5StickCPlus2/M5Unified.

---

### Task 1: Source Baseline

**Files:**
- Create: `docs/hardware/m5stickc-plus2-example-source.md`
- Create: `docs/superpowers/plans/2026-07-02-m5stickc-plus2-sensor-link-implementation.md`

- [x] **Step 1: Record official source**

Record official M5Stack source URLs, library version, and API observations.

- [x] **Step 2: Verify documentation files are readable**

Run: `rg --files docs`
Expected: lists PRD, v1 plan, design spec, source record, and this implementation plan.

### Task 2: PC Receiver Tests First

**Files:**
- Create: `tests/test_telemetry.py`
- Create: `tests/test_calibration.py`
- Create: `tests/test_jsonl_recorder.py`
- Create: `tests/test_simulated_ble_flow.py`

- [ ] **Step 1: Write failing tests**

Tests must cover valid telemetry, invalid JSON, missing fields, calibration center update, JSONL writing, and simulated notification flow.

- [ ] **Step 2: Run red tests**

Run: `uv run pytest`
Expected: FAIL because `pc_receiver` package does not exist.

### Task 3: PC Receiver Implementation

**Files:**
- Create: `pyproject.toml`
- Create: `pc_receiver/__init__.py`
- Create: `pc_receiver/telemetry.py`
- Create: `pc_receiver/calibration.py`
- Create: `pc_receiver/recorder.py`
- Create: `pc_receiver/transport.py`
- Create: `pc_receiver/app.py`

- [ ] **Step 1: Implement minimal code**

Implement parser, validation, calibration state, JSONL recorder, simulated notification runner, and BLE transport boundary.

- [ ] **Step 2: Run green tests**

Run: `uv run pytest`
Expected: all tests pass.

### Task 4: Firmware Static Tests First

**Files:**
- Create: `tests/test_firmware_static.py`

- [ ] **Step 1: Write failing firmware checks**

Tests must assert `platformio.ini` exists, firmware includes `M5StickCPlus2.h`, BLE notify code, JSON keys, frequency config, and no PotPlayer/Windows control strings.

- [ ] **Step 2: Run red firmware checks**

Run: `uv run pytest tests/test_firmware_static.py`
Expected: FAIL because firmware files do not exist.

### Task 5: Firmware Implementation

**Files:**
- Create: `platformio.ini`
- Create: `firmware/m5stickc_plus2_sensor_link/src/main.cpp`

- [ ] **Step 1: Implement PlatformIO firmware**

Create an Arduino ESP32 project using official M5StickCPlus2 APIs. Preserve display telemetry visualization and add BLE JSON notifications.

- [ ] **Step 2: Run static tests and build**

Run: `uv run pytest tests/test_firmware_static.py`
Expected: PASS.

Run: `pio run`
Expected: exit code 0 if dependencies resolve.

### Task 6: Final Verification

**Files:**
- Modify: `docs/plan/v1-index.md`
- Modify: `docs/plan/tashan-loop-log.md`

- [ ] **Step 1: Run verification**

Run: `uv run pytest`
Run: `rg --text -n "锛|€|俙|�|\\?\\?\\?|\\x00" .`
Run: `rg -n "PotPlayer|mouse_event|SendInput|pyautogui|win32gui|win32api" .`

- [ ] **Step 2: Record review and ship status**

Update v1 index with evidence, commit, and attempt push. If no remote exists, record `no_remote`.

## Self Review

- Spec coverage: REQ-0001-001 through REQ-0001-008 are mapped to tasks.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: PC parser emits `TelemetryPacket`; calibration consumes `TelemetryPacket`; recorder writes packet dicts.
