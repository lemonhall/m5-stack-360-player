from __future__ import annotations

import json

from pc_receiver.vlc_player_config import (
    DEFAULT_BLE_ADDRESS,
    DEFAULT_VLC_DIR,
    VlcPlayerConfig,
    load_config,
    save_config,
)


def test_load_config_missing_file_returns_defaults(tmp_path) -> None:
    config = load_config(tmp_path / "missing.json")

    assert config.vlc_dir == DEFAULT_VLC_DIR
    assert config.ble_address == DEFAULT_BLE_ADDRESS
    assert config.last_media == ""
    assert config.field_of_view == 80.0
    assert config.deadzone_degrees == 0.5


def test_load_config_merges_partial_file_with_defaults(tmp_path) -> None:
    path = tmp_path / "local.vlc-player.json"
    path.write_text(json.dumps({"ble_address": "AA:BB", "gain_yaw": 1.5}), encoding="utf-8")

    config = load_config(path)

    assert config.ble_address == "AA:BB"
    assert config.gain_yaw == 1.5
    assert config.vlc_dir == DEFAULT_VLC_DIR
    assert config.field_of_view == 80.0


def test_save_config_creates_parent_directory_and_round_trips(tmp_path) -> None:
    path = tmp_path / "config" / "local.vlc-player.json"
    original = VlcPlayerConfig(
        vlc_dir=r"D:\Program Files\VideoLAN\VLC",
        ble_address="0C:8B:95:B4:7B:5A",
        last_media=r"D:\video\sample.mp4",
        gain_yaw=1.2,
        gain_pitch=0.8,
        deadzone_degrees=0.25,
        field_of_view=75.0,
        auto_connect_ble=True,
        auto_play=True,
    )

    save_config(original, path)
    loaded = load_config(path)

    assert loaded == original
