from __future__ import annotations

from pc_receiver.vlc_viewpoint import ViewpointSettings, map_ypr_to_viewpoint


def test_map_ypr_to_viewpoint_applies_gain_and_axis_direction() -> None:
    settings = ViewpointSettings(gain_yaw=1.5, gain_pitch=2.0, field_of_view=72.0)

    viewpoint = map_ypr_to_viewpoint((10.0, -5.0, 2.0), settings)

    assert viewpoint.yaw == -15.0
    assert viewpoint.pitch == 10.0
    assert viewpoint.roll == 2.0
    assert viewpoint.field_of_view == 72.0


def test_map_ypr_to_viewpoint_applies_deadzone() -> None:
    settings = ViewpointSettings(deadzone_degrees=1.0)

    viewpoint = map_ypr_to_viewpoint((0.8, -0.5, 0.25), settings)

    assert viewpoint.yaw == 0.0
    assert viewpoint.pitch == 0.0
    assert viewpoint.roll == 0.0


def test_map_ypr_to_viewpoint_applies_video_front_offset_after_head_motion() -> None:
    settings = ViewpointSettings(
        gain_yaw=1.0,
        gain_pitch=1.0,
        front_yaw_degrees=180.0,
        front_pitch_degrees=5.0,
    )

    centered = map_ypr_to_viewpoint((0.0, 0.0, 0.0), settings)
    left_and_up = map_ypr_to_viewpoint((20.0, 10.0, 0.0), settings)

    assert centered.yaw == 180.0
    assert centered.pitch == 5.0
    assert left_and_up.yaw == 160.0
    assert left_and_up.pitch == -5.0


def test_map_ypr_to_viewpoint_clamps_yaw_to_configured_view_bounds() -> None:
    settings = ViewpointSettings(
        gain_yaw=1.0,
        front_yaw_degrees=90.0,
        min_yaw_degrees=0.0,
        max_yaw_degrees=180.0,
    )

    far_left = map_ypr_to_viewpoint((120.0, 0.0, 0.0), settings)
    far_right = map_ypr_to_viewpoint((-120.0, 0.0, 0.0), settings)

    assert far_left.yaw == 0.0
    assert far_right.yaw == 180.0


def test_map_ypr_to_viewpoint_applies_gain_before_configured_bounds() -> None:
    settings = ViewpointSettings(
        gain_yaw=2.0,
        gain_pitch=2.0,
        front_yaw_degrees=90.0,
        min_yaw_degrees=0.0,
        max_yaw_degrees=180.0,
        min_pitch_degrees=-25.0,
        max_pitch_degrees=25.0,
    )

    within_bounds = map_ypr_to_viewpoint((20.0, -10.0, 0.0), settings)
    beyond_bounds = map_ypr_to_viewpoint((60.0, -30.0, 0.0), settings)

    assert within_bounds.yaw == 50.0
    assert within_bounds.pitch == 20.0
    assert beyond_bounds.yaw == 0.0
    assert beyond_bounds.pitch == 25.0


def test_map_ypr_to_viewpoint_clamps_pitch_and_fov() -> None:
    settings = ViewpointSettings(gain_pitch=2.0, field_of_view=200.0)

    high = map_ypr_to_viewpoint((0.0, -80.0, 0.0), settings)
    low = map_ypr_to_viewpoint((0.0, 80.0, 0.0), settings)

    assert high.pitch == 90.0
    assert low.pitch == -90.0
    assert high.field_of_view == 150.0
