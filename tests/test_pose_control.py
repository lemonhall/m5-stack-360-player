from __future__ import annotations

from pc_receiver.pose_control import (
    PoseControlSettings,
    PoseController,
    learn_axis_mapping,
    learn_axis_mapping_with_magnitude,
    map_control_axes,
)


def test_learn_axis_mapping_chooses_largest_motion_axis_and_positive_sign() -> None:
    axis, sign = learn_axis_mapping((10.0, -2.0, 0.0), (12.0, -5.0, 18.0))

    assert axis == "roll"
    assert sign == 1.0


def test_learn_axis_mapping_inverts_negative_motion_to_positive_control() -> None:
    axis, sign = learn_axis_mapping((10.0, -2.0, 0.0), (8.0, -28.0, -4.0))

    assert axis == "pitch"
    assert sign == -1.0


def test_learn_axis_mapping_wraps_yaw_delta() -> None:
    axis, sign = learn_axis_mapping((179.0, 0.0, 0.0), (-170.0, 2.0, 1.0))

    assert axis == "yaw"
    assert sign == 1.0


def test_learn_axis_mapping_reports_largest_motion_magnitude() -> None:
    axis, sign, magnitude = learn_axis_mapping_with_magnitude((0.0, 0.0, 0.0), (1.0, -7.0, 3.0))

    assert axis == "pitch"
    assert sign == -1.0
    assert magnitude == 7.0


def test_map_control_axes_uses_configured_source_axes_and_signs() -> None:
    settings = PoseControlSettings(
        yaw_source_axis="roll",
        yaw_source_sign=-1.0,
        pitch_source_axis="yaw",
        pitch_source_sign=1.0,
    )

    assert map_control_axes((10.0, -20.0, 30.0), settings) == (-30.0, 10.0, 0.0)


def test_pose_controller_maps_axes_before_clamp_and_smoothing() -> None:
    controller = PoseController(
        PoseControlSettings(
            yaw_source_axis="roll",
            yaw_source_sign=-1.0,
            pitch_source_axis="pitch",
            pitch_source_sign=-1.0,
            max_yaw_degrees=25.0,
            max_pitch_degrees=15.0,
            smoothing_alpha=1.0,
            max_step_degrees=999.0,
        )
    )

    assert controller.update((5.0, -30.0, 40.0)) == (-25.0, 15.0, 0.0)


def test_pose_controller_clamps_relative_yaw_and_pitch_to_configured_view_box() -> None:
    controller = PoseController(
        PoseControlSettings(
            max_yaw_degrees=75.0,
            max_pitch_degrees=35.0,
            smoothing_alpha=1.0,
            max_step_degrees=999.0,
        )
    )

    assert controller.update((120.0, -80.0, 5.0)) == (75.0, -35.0, 0.0)


def test_pose_controller_smooths_small_jitter() -> None:
    controller = PoseController(
        PoseControlSettings(
            smoothing_alpha=0.25,
            max_step_degrees=999.0,
        )
    )

    assert controller.update((0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)
    assert controller.update((4.0, 0.0, 0.0)) == (1.0, 0.0, 0.0)


def test_pose_controller_limits_per_packet_step() -> None:
    controller = PoseController(
        PoseControlSettings(
            smoothing_alpha=1.0,
            max_step_degrees=3.0,
        )
    )

    assert controller.update((0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)
    assert controller.update((20.0, -20.0, 0.0)) == (3.0, -3.0, 0.0)


def test_pose_controller_reset_returns_to_center_immediately() -> None:
    controller = PoseController(PoseControlSettings(smoothing_alpha=0.2, max_step_degrees=3.0))
    controller.update((30.0, 0.0, 0.0))

    assert controller.reset() == (0.0, 0.0, 0.0)
    assert controller.update((0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)
