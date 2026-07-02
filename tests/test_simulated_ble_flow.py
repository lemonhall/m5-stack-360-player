import json
import asyncio

from pc_receiver.app import run_async_packets, run_packets


def test_run_packets_parses_calibrates_and_logs(tmp_path):
    log_path = tmp_path / "flow.jsonl"
    raw_packets = [
        json.dumps(
            {
                "seq": 1,
                "ms": 100,
                "ypr": [10.0, 0.0, 0.0],
                "acc": [0.0, 0.0, 1.0],
                "gyro": [0.0, 0.0, 0.0],
                "btn": 1,
            }
        ),
        json.dumps(
            {
                "seq": 2,
                "ms": 133,
                "ypr": [12.0, -1.0, 0.5],
                "acc": [0.0, 0.0, 1.0],
                "gyro": [0.0, 0.0, 0.0],
                "btn": 0,
            }
        ),
    ]

    summaries = run_packets(raw_packets, log_path)

    assert [summary.seq for summary in summaries] == [1, 2]
    assert summaries[0].center_updated is True
    assert summaries[1].relative_ypr == (2.0, -1.0, 0.5)
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 2


def test_run_async_packets_stops_after_max_packets(tmp_path):
    async def stream():
        for seq in range(1, 4):
            yield json.dumps(
                {
                    "seq": seq,
                    "ms": seq * 33,
                    "ypr": [float(seq), 0.0, 0.0],
                    "acc": [0.0, 0.0, 1.0],
                    "gyro": [0.0, 0.0, 0.0],
                    "btn": 0,
                }
            ).encode("utf-8")

    log_path = tmp_path / "async-flow.jsonl"

    summaries = asyncio.run(run_async_packets(stream(), log_path, max_packets=2))

    assert [summary.seq for summary in summaries] == [1, 2]
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 2
