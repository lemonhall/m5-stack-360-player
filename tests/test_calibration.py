from pc_receiver.calibration import CalibrationState
from pc_receiver.telemetry import TelemetryPacket


def packet(seq, ypr, btn=False):
    return TelemetryPacket(
        seq=seq,
        ms=seq * 100,
        ypr=ypr,
        quat=None,
        acc=(0.0, 0.0, 1.0),
        gyro=(0.0, 0.0, 0.0),
        btn=btn,
    )


def test_calibration_does_not_set_center_before_button_press():
    state = CalibrationState()

    view = state.update(packet(1, (10.0, 5.0, 1.0), btn=False))

    assert state.center_ypr is None
    assert view.relative_ypr is None
    assert view.center_updated is False


def test_calibration_sets_center_on_button_press():
    state = CalibrationState()

    view = state.update(packet(2, (10.0, 5.0, 1.0), btn=True))

    assert state.center_ypr == (10.0, 5.0, 1.0)
    assert view.relative_ypr == (0.0, 0.0, 0.0)
    assert view.center_updated is True


def test_calibration_reports_relative_ypr_after_center_is_set():
    state = CalibrationState()
    state.update(packet(3, (10.0, 5.0, 1.0), btn=True))

    view = state.update(packet(4, (12.5, 2.0, 1.5), btn=False))

    assert view.relative_ypr == (2.5, -3.0, 0.5)
    assert view.center_updated is False


def test_calibration_wraps_yaw_to_shortest_delta():
    state = CalibrationState()
    state.update(packet(5, (179.0, 0.0, 0.0), btn=True))

    view = state.update(packet(6, (-179.0, 0.0, 0.0), btn=False))

    assert view.relative_ypr == (2.0, 0.0, 0.0)
