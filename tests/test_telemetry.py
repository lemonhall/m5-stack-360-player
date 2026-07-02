import json

import pytest

from pc_receiver.telemetry import TelemetryError, TelemetryPacket, parse_telemetry


def test_parse_telemetry_accepts_required_fields_with_ypr():
    raw = json.dumps(
        {
            "seq": 7,
            "ms": 1200,
            "ypr": [1.0, -2.0, 3.5],
            "acc": [0.1, 0.2, 0.98],
            "gyro": [0.01, -0.02, 0.03],
            "btn": 0,
        }
    )

    packet = parse_telemetry(raw)

    assert packet == TelemetryPacket(
        seq=7,
        ms=1200,
        ypr=(1.0, -2.0, 3.5),
        quat=None,
        acc=(0.1, 0.2, 0.98),
        gyro=(0.01, -0.02, 0.03),
        btn=False,
    )


def test_parse_telemetry_accepts_quat_without_ypr():
    raw = json.dumps(
        {
            "seq": 8,
            "ms": 1300,
            "quat": [1.0, 0.0, 0.0, 0.0],
            "acc": [0.0, 0.0, 1.0],
            "gyro": [0.0, 0.0, 0.0],
            "btn": 1,
        }
    )

    packet = parse_telemetry(raw)

    assert packet.quat == (1.0, 0.0, 0.0, 0.0)
    assert packet.ypr is None
    assert packet.btn is True


def test_parse_telemetry_rejects_invalid_json():
    with pytest.raises(TelemetryError, match="invalid JSON"):
        parse_telemetry("{not-json")


def test_parse_telemetry_rejects_missing_required_field():
    raw = json.dumps(
        {
            "seq": 9,
            "ms": 1400,
            "ypr": [1.0, 2.0, 3.0],
            "acc": [0.0, 0.0, 1.0],
            "btn": 0,
        }
    )

    with pytest.raises(TelemetryError, match="missing field: gyro"):
        parse_telemetry(raw)


def test_parse_telemetry_rejects_packet_without_pose():
    raw = json.dumps(
        {
            "seq": 10,
            "ms": 1500,
            "acc": [0.0, 0.0, 1.0],
            "gyro": [0.0, 0.0, 0.0],
            "btn": 0,
        }
    )

    with pytest.raises(TelemetryError, match="missing pose"):
        parse_telemetry(raw)


def test_parse_telemetry_rejects_wrong_vector_length():
    raw = json.dumps(
        {
            "seq": 11,
            "ms": 1600,
            "ypr": [1.0, 2.0],
            "acc": [0.0, 0.0, 1.0],
            "gyro": [0.0, 0.0, 0.0],
            "btn": 0,
        }
    )

    with pytest.raises(TelemetryError, match="ypr must contain 3 numbers"):
        parse_telemetry(raw)
