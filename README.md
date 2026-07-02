# M5StickC Plus2 360 Sensor Link

v1 turns an M5StickC Plus2 into a head-pose telemetry device for later PotPlayer 360 VR view control.

## Firmware

Build:

```powershell
pio run
```

Upload to the connected M5StickC Plus2:

```powershell
pio run -t upload --upload-port COM5
```

The firmware advertises BLE device name `M5HeadTracker` and sends JSON telemetry at about 30 Hz.

Telemetry characteristic UUID:

```text
7d2f4b8a-6d0e-4f88-9e1f-0c8d2f5f5a02
```

## PC Receiver

Run tests:

```powershell
uv run --no-sync pytest
```

Run BLE receiver after installing the optional BLE dependency:

```powershell
uv run --extra ble m5-telemetry --address <BLE_ADDRESS> --log logs/telemetry.jsonl
```

Run the tkinter visualizer:

```powershell
uv run --extra ble m5-visualizer --address <BLE_ADDRESS>
```

## v1 Boundary

v1 does not control PotPlayer, does not move the mouse, and does not call Windows window-control APIs. The visualizer is a diagnostic PC preview only.
