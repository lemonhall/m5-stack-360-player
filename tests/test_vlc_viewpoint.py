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


def test_map_ypr_to_viewpoint_clamps_pitch_and_fov() -> None:
    settings = ViewpointSettings(gain_pitch=2.0, field_of_view=200.0)

    high = map_ypr_to_viewpoint((0.0, -80.0, 0.0), settings)
    low = map_ypr_to_viewpoint((0.0, 80.0, 0.0), settings)

    assert high.pitch == 90.0
    assert low.pitch == -90.0
    assert high.field_of_view == 150.0
