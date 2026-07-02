from __future__ import annotations

from dataclasses import dataclass

from pc_receiver.telemetry import TelemetryPacket, Vector3


@dataclass(frozen=True)
class PacketView:
    seq: int
    absolute_ypr: Vector3 | None
    relative_ypr: Vector3 | None
    center_updated: bool


class CalibrationState:
    def __init__(self) -> None:
        self.center_ypr: Vector3 | None = None

    def update(self, packet: TelemetryPacket) -> PacketView:
        center_updated = False
        if packet.btn and packet.ypr is not None:
            self.center_ypr = packet.ypr
            center_updated = True

        relative_ypr = None
        if packet.ypr is not None and self.center_ypr is not None:
            relative_ypr = (
                _wrap_degrees(packet.ypr[0] - self.center_ypr[0]),
                packet.ypr[1] - self.center_ypr[1],
                packet.ypr[2] - self.center_ypr[2],
            )

        return PacketView(
            seq=packet.seq,
            absolute_ypr=packet.ypr,
            relative_ypr=relative_ypr,
            center_updated=center_updated,
        )


def _wrap_degrees(value: float) -> float:
    while value <= -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value
