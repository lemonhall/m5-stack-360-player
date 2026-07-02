from __future__ import annotations

from pc_receiver.pose_control import PoseControlSettings, PoseController


def test_pose_controller_clamps_relative_yaw_and_pitch_to_configured_view_box() -> None:
    controller = PoseController(
        PoseControlSettings(
            max_yaw_degrees=75.0,
            max_pitch_degrees=35.0,
            smoothing_alpha=1.0,
            max_step_degrees=999.0,
        )
    )

    assert controller.update((120.0, -80.0, 5.0)) == (75.0, -35.0, 5.0)


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
