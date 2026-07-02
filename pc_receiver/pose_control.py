from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pc_receiver.telemetry import Vector3

AxisName = Literal["yaw", "pitch", "roll"]


@dataclass(frozen=True)
class PoseControlSettings:
    max_yaw_degrees: float = 90.0
    max_pitch_degrees: float = 45.0
    smoothing_alpha: float = 0.25
    max_step_degrees: float = 6.0
    yaw_source_axis: AxisName = "yaw"
    yaw_source_sign: float = 1.0
    pitch_source_axis: AxisName = "pitch"
    pitch_source_sign: float = 1.0


class PoseController:
    def __init__(self, settings: PoseControlSettings) -> None:
        self.settings = settings
        self._filtered: Vector3 | None = None

    def update(self, relative_ypr: Vector3) -> Vector3:
        control_ypr = map_control_axes(relative_ypr, self.settings)
        target = (
            _clamp(control_ypr[0], -self.settings.max_yaw_degrees, self.settings.max_yaw_degrees),
            _clamp(
                control_ypr[1],
                -self.settings.max_pitch_degrees,
                self.settings.max_pitch_degrees,
            ),
            control_ypr[2],
        )
        if self._filtered is None:
            self._filtered = target
            return target

        alpha = _clamp(self.settings.smoothing_alpha, 0.0, 1.0)
        stepped = tuple(
            _step_toward(current, goal, self.settings.max_step_degrees)
            for current, goal in zip(self._filtered, target, strict=True)
        )
        self._filtered = tuple(
            current + (goal - current) * alpha
            for current, goal in zip(self._filtered, stepped, strict=True)
        )
        return self._filtered

    def reset(self) -> Vector3:
        self._filtered = (0.0, 0.0, 0.0)
        return self._filtered


def map_control_axes(relative_ypr: Vector3, settings: PoseControlSettings) -> Vector3:
    return (
        _axis_value(relative_ypr, settings.yaw_source_axis) * _sign(settings.yaw_source_sign),
        _axis_value(relative_ypr, settings.pitch_source_axis) * _sign(settings.pitch_source_sign),
        0.0,
    )


def learn_axis_mapping(start_ypr: Vector3, end_ypr: Vector3) -> tuple[AxisName, float]:
    axis, sign, _ = learn_axis_mapping_with_magnitude(start_ypr, end_ypr)
    return axis, sign


def learn_axis_mapping_with_magnitude(start_ypr: Vector3, end_ypr: Vector3) -> tuple[AxisName, float, float]:
    deltas: dict[AxisName, float] = {
        "yaw": _wrap_degrees(end_ypr[0] - start_ypr[0]),
        "pitch": end_ypr[1] - start_ypr[1],
        "roll": end_ypr[2] - start_ypr[2],
    }
    axis = max(deltas, key=lambda name: abs(deltas[name]))
    return axis, _sign(deltas[axis]), abs(deltas[axis])


def _axis_value(ypr: Vector3, axis: str) -> float:
    if axis == "yaw":
        return ypr[0]
    if axis == "pitch":
        return ypr[1]
    if axis == "roll":
        return ypr[2]
    return ypr[0]


def _sign(value: float) -> float:
    return -1.0 if value < 0.0 else 1.0


def _wrap_degrees(value: float) -> float:
    while value <= -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value


def _step_toward(current: float, target: float, max_step: float) -> float:
    step = abs(max_step)
    delta = target - current
    if abs(delta) <= step:
        return target
    return current + step * (1.0 if delta > 0.0 else -1.0)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
