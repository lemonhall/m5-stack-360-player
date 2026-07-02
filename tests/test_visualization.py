from __future__ import annotations

import math

from pc_receiver.visualization import (
    CuboidModel,
    project_points,
    rotation_matrix_from_ypr,
    transform_points,
)


def test_neutral_orientation_keeps_stick_horizontal() -> None:
    model = CuboidModel.stick()
    points = transform_points(model.vertices, rotation_matrix_from_ypr((0.0, 0.0, 0.0)))
    projected = project_points(points, width=800, height=600)

    left = projected[0]
    right = projected[1]

    assert left[0] < 400
    assert right[0] > 400
    assert abs(left[1] - right[1]) < 1.0


def test_yaw_rotates_stick_projection() -> None:
    model = CuboidModel.stick()
    neutral = project_points(
        transform_points(model.vertices, rotation_matrix_from_ypr((0.0, 0.0, 0.0))),
        width=800,
        height=600,
    )
    yawed = project_points(
        transform_points(model.vertices, rotation_matrix_from_ypr((90.0, 0.0, 0.0))),
        width=800,
        height=600,
    )

    neutral_span_x = abs(neutral[1][0] - neutral[0][0])
    yawed_span_x = abs(yawed[1][0] - yawed[0][0])
    yawed_span_y = abs(yawed[1][1] - yawed[0][1])

    assert yawed_span_x < neutral_span_x * 0.25
    assert yawed_span_y > neutral_span_x * 0.75


def test_projected_points_are_finite() -> None:
    model = CuboidModel.stick()
    points = transform_points(
        model.vertices,
        rotation_matrix_from_ypr((-37.0, 22.0, 15.0)),
    )
    projected = project_points(points, width=640, height=480)

    assert len(projected) == len(model.vertices)
    assert all(math.isfinite(coord) for point in projected for coord in point)
