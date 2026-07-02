from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
FIRMWARE = ROOT / "firmware" / "m5stickc_plus2_sensor_link" / "src" / "main.cpp"


def test_platformio_project_exists_for_m5stickc_plus2():
    text = PLATFORMIO.read_text(encoding="utf-8")

    assert "[env:m5stick-c-plus2]" in text
    assert "board = m5stick-c" in text
    assert "M5StickCPlus2" in text


def test_firmware_uses_official_m5stickcplus2_imu_api():
    text = FIRMWARE.read_text(encoding="utf-8")

    assert '#include "M5StickCPlus2.h"' in text
    assert "StickCP2.Imu.update()" in text
    assert "StickCP2.Imu.getImuData()" in text


def test_firmware_defines_ble_telemetry_service_and_notify():
    text = FIRMWARE.read_text(encoding="utf-8")

    assert "M5_HEAD_TRACKER_SERVICE_UUID" in text
    assert "M5_TELEMETRY_CHARACTERISTIC_UUID" in text
    assert "BLECharacteristic" in text
    assert "->notify()" in text or ".notify()" in text


def test_firmware_json_contains_required_telemetry_keys():
    text = FIRMWARE.read_text(encoding="utf-8")

    for key in ("seq", "ms", "ypr", "acc", "gyro", "btn"):
        assert key in text


def test_firmware_has_configurable_default_telemetry_hz():
    text = FIRMWARE.read_text(encoding="utf-8")

    assert "TELEMETRY_HZ" in text
    assert "30" in text


def test_firmware_avoids_m5_update_crash_path_for_button_input():
    text = FIRMWARE.read_text(encoding="utf-8")

    assert "MAIN_BUTTON_PIN" in text
    assert "digitalRead(MAIN_BUTTON_PIN)" in text
    assert "INPUT_PULLUP" in text
    assert "digitalRead(MAIN_BUTTON_PIN) == LOW" in text
    assert "centerButtonPending" in text
    assert "StickCP2.update()" not in text


def test_firmware_does_not_contain_potplayer_or_windows_control_logic():
    haystack = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [FIRMWARE]
        if path.exists()
    )

    forbidden = [
        "PotPlayer",
        "mouse_event",
        "SendInput",
        "pyautogui",
        "win32gui",
        "win32api",
    ]
    for token in forbidden:
        assert token not in haystack
