from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any


DEFAULT_VLC_DIR = r"D:\Program Files\VideoLAN\VLC"
DEFAULT_BLE_ADDRESS = "0C:8B:95:B4:7B:5A"
DEFAULT_CONFIG_PATH = Path("config/local.vlc-player.json")


@dataclass(frozen=True)
class VlcPlayerConfig:
    vlc_dir: str = DEFAULT_VLC_DIR
    ble_address: str = DEFAULT_BLE_ADDRESS
    last_media: str = ""
    gain_yaw: float = 1.0
    gain_pitch: float = 1.0
    deadzone_degrees: float = 0.5
    field_of_view: float = 80.0
    serve_spherical_metadata: bool = True
    auto_connect_ble: bool = False
    auto_play: bool = False


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> VlcPlayerConfig:
    config_path = Path(path)
    if not config_path.exists():
        return VlcPlayerConfig()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config must be a JSON object")

    valid_names = {field.name for field in fields(VlcPlayerConfig)}
    filtered: dict[str, Any] = {key: value for key, value in payload.items() if key in valid_names}
    return VlcPlayerConfig(**filtered)


def save_config(config: VlcPlayerConfig, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
