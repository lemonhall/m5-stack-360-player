# Tk Visualizer Design

## Goal

Build a small PC-side Python visualizer that shows the M5StickC Plus2 as an orange 3D stick/cuboid whose orientation follows live BLE telemetry.

## Scope

- Add a `m5-visualizer` console script.
- Reuse the existing BLE notification transport, telemetry parser, and calibration state.
- Use only Python standard library GUI components: `tkinter` and `Canvas`.
- Render a simple 3D perspective projection of a long cuboid, plus lightweight text status.
- Keep PotPlayer control, mouse simulation, OpenGL, and external GUI dependencies out of scope.

## UX

The first screen is the usable visualizer window. It contains a dark canvas, a small coordinate axis, and an orange stick/cuboid. Incoming `ypr` telemetry rotates the cuboid. Pressing the M5 main button continues to update center calibration through the existing `CalibrationState`; when a relative pose is available, the visualizer renders the relative pose.

## Architecture

- `pc_receiver.visualization`: pure geometry and projection functions. This module has no BLE or tkinter dependency and is unit-tested.
- `pc_receiver.visualizer_app`: tkinter window, BLE worker thread, queue handoff, and repaint loop.
- Existing `pc_receiver.transport.iter_ble_notifications` remains the BLE source.
- Existing `pc_receiver.telemetry.parse_telemetry` remains the protocol parser.
- Existing `pc_receiver.calibration.CalibrationState` remains the center-pose owner.

## Data Flow

`BLE notification -> parse_telemetry -> CalibrationState.update -> VisualizerSnapshot -> Tk queue -> Canvas redraw`

The BLE loop runs in a background thread with its own asyncio loop. Tk stays on the main thread. The background thread only posts immutable snapshots and error/status messages into a standard `queue.Queue`.

## Error Handling

- Missing `--address` exits through argparse.
- BLE exceptions are shown in the window status line and printed to stderr.
- Malformed packets are skipped and counted as parse errors.
- If no packets have arrived yet, the canvas shows a neutral stick and `waiting`.

## Verification

- Unit tests cover yaw/pitch/roll rotation behavior and 2D projection output.
- Existing parser/calibration tests remain unchanged.
- Manual/live verification uses:
  `uv run --extra ble m5-visualizer --address 0C:8B:95:B4:7B:5A`

