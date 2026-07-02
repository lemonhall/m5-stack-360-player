from __future__ import annotations

from dataclasses import dataclass

from pc_receiver.telemetry import Vector3


@dataclass(frozen=True)
class PoseControlSettings:
    max_yaw_degrees: float = 90.0
    max_pitch_degrees: float = 45.0
    smoothing_alpha: float = 0.25
    max_step_degrees: float = 6.0


class PoseController:
    def __init__(self, settings: PoseControlSettings) -> None:
        self.settings = settings
        self._filtered: Vector3 | None = None

    def update(self, relative_ypr: Vector3) -> Vector3:
        target = (
            _clamp(relative_ypr[0], -self.settings.max_yaw_degrees, self.settings.max_yaw_degrees),
            _clamp(
                relative_ypr[1],
                -self.settings.max_pitch_degrees,
                self.settings.max_pitch_degrees,
            ),
            relative_ypr[2],
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


def _step_toward(current: float, target: float, max_step: float) -> float:
    step = abs(max_step)
    delta = target - current
    if abs(delta) <= step:
        return target
    return current + step * (1.0 if delta > 0.0 else -1.0)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
