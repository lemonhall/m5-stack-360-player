from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Iterable

from pc_receiver.calibration import CalibrationState, PacketView
from pc_receiver.recorder import JsonlRecorder
from pc_receiver.telemetry import parse_telemetry
from pc_receiver.transport import iter_ble_notifications


DEFAULT_CHARACTERISTIC_UUID = "7d2f4b8a-6d0e-4f88-9e1f-0c8d2f5f5a02"


def run_packets(raw_packets: Iterable[str | bytes], log_path: str | Path) -> list[PacketView]:
    state = CalibrationState()
    summaries: list[PacketView] = []
    with JsonlRecorder(log_path) as recorder:
        for raw in raw_packets:
            packet = parse_telemetry(raw)
            view = state.update(packet)
            recorder.write(
                packet,
                relative_ypr=view.relative_ypr,
                center_updated=view.center_updated,
            )
            summaries.append(view)
    return summaries


async def run_async_packets(
    raw_packets: AsyncIterable[str | bytes],
    log_path: str | Path,
    *,
    max_packets: int | None = None,
) -> list[PacketView]:
    state = CalibrationState()
    summaries: list[PacketView] = []
    with JsonlRecorder(log_path) as recorder:
        async for raw in raw_packets:
            packet = parse_telemetry(raw)
            view = state.update(packet)
            recorder.write(
                packet,
                relative_ypr=view.relative_ypr,
                center_updated=view.center_updated,
            )
            summaries.append(view)
            _print_view(view)
            if max_packets is not None and len(summaries) >= max_packets:
                break
    return summaries


async def run_ble(
    address: str,
    log_path: str | Path,
    *,
    characteristic_uuid: str = DEFAULT_CHARACTERISTIC_UUID,
    max_packets: int | None = None,
) -> list[PacketView]:
    return await run_async_packets(
        iter_ble_notifications(address, characteristic_uuid),
        log_path,
        max_packets=max_packets,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Receive M5StickC Plus2 telemetry")
    parser.add_argument("--log", default="logs/telemetry.jsonl", help="JSONL log path")
    parser.add_argument("--address", help="BLE device address")
    parser.add_argument(
        "--characteristic",
        default=DEFAULT_CHARACTERISTIC_UUID,
        help="BLE telemetry characteristic UUID",
    )
    parser.add_argument("--max-packets", type=int, help="stop after N packets")
    args = parser.parse_args(argv)
    if not args.address:
        parser.error("--address is required for BLE live mode")
    asyncio.run(
        run_ble(
            args.address,
            args.log,
            characteristic_uuid=args.characteristic,
            max_packets=args.max_packets,
        )
    )
    return 0


def _print_view(view: PacketView) -> None:
    center = " center" if view.center_updated else ""
    print(
        f"seq={view.seq} absolute={view.absolute_ypr} "
        f"relative={view.relative_ypr}{center}",
        flush=True,
    )
