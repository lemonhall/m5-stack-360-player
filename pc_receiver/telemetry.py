from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


class TelemetryError(ValueError):
    """Raised when a telemetry packet is malformed."""


Vector3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]


@dataclass(frozen=True)
class TelemetryPacket:
    seq: int
    ms: int
    ypr: Vector3 | None
    quat: Quat | None
    acc: Vector3
    gyro: Vector3
    btn: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "ms": self.ms,
            "ypr": list(self.ypr) if self.ypr is not None else None,
            "quat": list(self.quat) if self.quat is not None else None,
            "acc": list(self.acc),
            "gyro": list(self.gyro),
            "btn": self.btn,
        }


def parse_telemetry(raw: str | bytes) -> TelemetryPacket:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TelemetryError("invalid JSON") from exc

    if not isinstance(payload, dict):
        raise TelemetryError("packet must be a JSON object")

    for field in ("seq", "ms", "acc", "gyro", "btn"):
        if field not in payload:
            raise TelemetryError(f"missing field: {field}")

    ypr = _optional_vector3(payload, "ypr")
    quat = _optional_quat(payload, "quat")
    if ypr is None and quat is None:
        raise TelemetryError("missing pose: expected ypr or quat")

    return TelemetryPacket(
        seq=_int_field(payload, "seq"),
        ms=_int_field(payload, "ms"),
        ypr=ypr,
        quat=quat,
        acc=_required_vector3(payload, "acc"),
        gyro=_required_vector3(payload, "gyro"),
        btn=bool(payload["btn"]),
    )


def _int_field(payload: dict[str, Any], field: str) -> int:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TelemetryError(f"{field} must be an integer")
    return value


def _required_vector3(payload: dict[str, Any], field: str) -> Vector3:
    if field not in payload:
        raise TelemetryError(f"missing field: {field}")
    return _vector(payload[field], field, 3)  # type: ignore[return-value]


def _optional_vector3(payload: dict[str, Any], field: str) -> Vector3 | None:
    if field not in payload or payload[field] is None:
        return None
    return _vector(payload[field], field, 3)  # type: ignore[return-value]


def _optional_quat(payload: dict[str, Any], field: str) -> Quat | None:
    if field not in payload or payload[field] is None:
        return None
    return _vector(payload[field], field, 4)  # type: ignore[return-value]


def _vector(value: Any, field: str, length: int) -> tuple[float, ...]:
    if not isinstance(value, list | tuple) or len(value) != length:
        raise TelemetryError(f"{field} must contain {length} numbers")
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise TelemetryError(f"{field} must contain {length} numbers")
        numbers.append(float(item))
    return tuple(numbers)
