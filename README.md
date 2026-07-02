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

Run the VLC 360 player GUI:

```powershell
uv run --extra player m5-vlc-player
```

The player reads and writes local settings at:

```text
config/local.vlc-player.json
```

The default VLC directory is `D:\Program Files\VideoLAN\VLC`. VLC 3.x must be installed locally. Codec support is provided by VLC/libVLC itself; this project does not install codecs or transcode video.

The VLC player defaults to preparing a cached MP4 copy with Google spherical metadata for local 2:1 VR files that PotPlayer plays with its `Equirectangular` 360 menu item. VLC then opens the cached copy so its normal 360 renderer and viewpoint API can work even when the original MP4 does not carry spherical metadata.

## v1 Boundary

v1 does not control PotPlayer, does not move the mouse, and does not call Windows window-control APIs. The visualizer is a diagnostic PC preview only.

## v2 Boundary

v2 uses embedded VLC/libVLC for 360 playback and viewpoint control. It does not control PotPlayer and does not simulate mouse or keyboard input.
