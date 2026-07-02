# Tk Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tkinter PC visualizer that renders live M5StickC Plus2 BLE orientation as an orange 3D stick.

**Architecture:** Keep geometry pure and tested in `pc_receiver.visualization`; keep tkinter and BLE thread orchestration in `pc_receiver.visualizer_app`. Reuse existing parser, BLE transport, recorder-free calibration state, and project script wiring.

**Tech Stack:** Python 3.13, tkinter, asyncio, bleak optional extra, pytest.

---

### Task 1: Pure 3D Geometry

**Files:**
- Create: `pc_receiver/visualization.py`
- Create: `tests/test_visualization.py`

- [ ] **Step 1: Write failing tests**

Create tests that assert neutral orientation projects a horizontal stick, yaw changes the endpoint positions, and projection returns finite 2D points.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests\test_visualization.py`
Expected: fail because `pc_receiver.visualization` does not exist.

- [ ] **Step 3: Implement geometry**

Create `CuboidModel`, `rotation_matrix_from_ypr`, `transform_points`, and `project_points`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests\test_visualization.py`
Expected: pass.

### Task 2: Tkinter Visualizer App

**Files:**
- Create: `pc_receiver/visualizer_app.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_python_runtime_policy.py`

- [ ] **Step 1: Write failing script metadata test**

Add an assertion that `project.scripts["m5-visualizer"] == "pc_receiver.visualizer_app:main"`.

- [ ] **Step 2: Run test**

Run: `python -m pytest tests\test_python_runtime_policy.py`
Expected: fail because the script is not declared.

- [ ] **Step 3: Implement app and script**

Add a tkinter app that starts a BLE worker thread, receives snapshots through `queue.Queue`, and redraws the cuboid on a canvas. Add the `m5-visualizer` script in `pyproject.toml`.

- [ ] **Step 4: Verify metadata and import**

Run: `python -m pytest tests\test_python_runtime_policy.py`
Run: `uv run --extra ble python -c "from pc_receiver.visualizer_app import main; print(main is not None)"`
Expected: both pass.

### Task 3: Integration Verification

**Files:**
- Modify: `docs/plan/v1-index.md`

- [ ] **Step 1: Run full tests**

Run: `python -m pytest`
Expected: all tests pass.

- [ ] **Step 2: Run script help**

Run: `uv run --extra ble m5-visualizer --help`
Expected: argparse help prints and exits 0.

- [ ] **Step 3: Update documentation**

Record the visualizer command and verification status in `docs/plan/v1-index.md`.

