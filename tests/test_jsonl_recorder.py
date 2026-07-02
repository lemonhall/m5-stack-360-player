import json

from pc_receiver.recorder import JsonlRecorder
from pc_receiver.telemetry import TelemetryPacket


def test_jsonl_recorder_writes_one_parseable_line_per_packet(tmp_path):
    log_path = tmp_path / "telemetry.jsonl"
    packet = TelemetryPacket(
        seq=1,
        ms=100,
        ypr=(1.0, 2.0, 3.0),
        quat=None,
        acc=(0.1, 0.2, 0.3),
        gyro=(0.4, 0.5, 0.6),
        btn=False,
    )

    with JsonlRecorder(log_path) as recorder:
        recorder.write(packet, relative_ypr=(0.0, 0.0, 0.0), center_updated=True)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["seq"] == 1
    assert record["relative_ypr"] == [0.0, 0.0, 0.0]
    assert record["center_updated"] is True
