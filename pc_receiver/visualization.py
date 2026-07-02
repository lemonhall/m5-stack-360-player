from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TypeAlias


Point3: TypeAlias = tuple[float, float, float]
Point2: TypeAlias = tuple[float, float]
Matrix3: TypeAlias = tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class CuboidModel:
    vertices: tuple[Point3, ...]
    edges: tuple[tuple[int, int], ...]
    faces: tuple[tuple[int, int, int, int], ...]

    @classmethod
    def stick(
        cls,
        *,
        length: float = 4.0,
        width: float = 0.55,
        height: float = 0.35,
    ) -> "CuboidModel":
        half_l = length / 2.0
        half_w = width / 2.0
        half_h = height / 2.0
        vertices = (
            (-half_l, 0.0, 0.0),
            (half_l, 0.0, 0.0),
            (-half_l, -half_w, -half_h),
            (half_l, -half_w, -half_h),
            (half_l, half_w, -half_h),
            (-half_l, half_w, -half_h),
            (-half_l, -half_w, half_h),
            (half_l, -half_w, half_h),
            (half_l, half_w, half_h),
            (-half_l, half_w, half_h),
        )
        return cls(
            vertices=vertices,
            edges=(
                (0, 1),
                (2, 3),
                (3, 4),
                (4, 5),
                (5, 2),
                (6, 7),
                (7, 8),
                (8, 9),
                (9, 6),
                (2, 6),
                (3, 7),
                (4, 8),
                (5, 9),
            ),
            faces=(
                (2, 3, 4, 5),
                (6, 7, 8, 9),
                (2, 3, 7, 6),
                (3, 4, 8, 7),
                (4, 5, 9, 8),
                (5, 2, 6, 9),
            ),
        )


def rotation_matrix_from_ypr(ypr: tuple[float, float, float]) -> Matrix3:
    yaw, pitch, roll = (math.radians(value) for value in ypr)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)

    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def transform_points(points: tuple[Point3, ...], matrix: Matrix3) -> tuple[Point3, ...]:
    transformed: list[Point3] = []
    for x, y, z in points:
        transformed.append(
            (
                matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z,
                matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z,
                matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z,
            )
        )
    return tuple(transformed)


def project_points(
    points: tuple[Point3, ...],
    *,
    width: int,
    height: int,
    scale: float | None = None,
    camera_distance: float = 8.0,
) -> tuple[Point2, ...]:
    if scale is None:
        scale = min(width, height) * 0.16

    projected: list[Point2] = []
    center_x = width / 2.0
    center_y = height / 2.0
    for x, y, z in points:
        depth = max(0.1, camera_distance - z)
        perspective = camera_distance / depth
        projected.append(
            (
                center_x + x * scale * perspective,
                center_y - y * scale * perspective,
            )
        )
    return tuple(projected)
