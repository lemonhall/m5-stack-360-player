from __future__ import annotations

from dataclasses import dataclass

from pc_receiver.telemetry import Vector3


@dataclass(frozen=True)
class VlcViewpoint:
    yaw: float
    pitch: float
    roll: float
    field_of_view: float


@dataclass(frozen=True)
class ViewpointSettings:
    gain_yaw: float = 1.0
    gain_pitch: float = 1.0
    deadzone_degrees: float = 0.5
    field_of_view: float = 80.0
    front_yaw_degrees: float = 0.0
    front_pitch_degrees: float = 0.0
    min_yaw_degrees: float = -180.0
    max_yaw_degrees: float = 180.0
    min_pitch_degrees: float = -90.0
    max_pitch_degrees: float = 90.0


def map_ypr_to_viewpoint(ypr: Vector3, settings: ViewpointSettings) -> VlcViewpoint:
    yaw, pitch, roll = (_apply_deadzone(value, settings.deadzone_degrees) for value in ypr)
    return VlcViewpoint(
        yaw=_clamp(
            settings.front_yaw_degrees - yaw * settings.gain_yaw,
            settings.min_yaw_degrees,
            settings.max_yaw_degrees,
        ),
        pitch=_clamp(
            settings.front_pitch_degrees - pitch * settings.gain_pitch,
            settings.min_pitch_degrees,
            settings.max_pitch_degrees,
        ),
        roll=_clamp(roll, -180.0, 180.0),
        field_of_view=_clamp(settings.field_of_view, 20.0, 150.0),
    )


def _apply_deadzone(value: float, deadzone: float) -> float:
    return 0.0 if abs(value) < deadzone else value


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
