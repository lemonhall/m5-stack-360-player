from __future__ import annotations

from pathlib import Path

import pytest

from pc_receiver.vlc_backend import validate_vlc_dir
from queue import Queue

from pc_receiver.vlc_player_app import (
    PlayerMessage,
    VlcPlayerController,
    _prepare_media_path_for_vlc,
    _relative_ypr,
    _start_media_prepare_thread,
)
from pc_receiver.vlc_player_config import VlcPlayerConfig
from pc_receiver.vlc_viewpoint import VlcViewpoint
from pc_receiver.virtual_mp4_server import VirtualMp4Server


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []
        self.media_path: str | None = None
        self.viewpoint: VlcViewpoint | None = None

    def attach_to_window(self, hwnd: int) -> None:
        self.calls.append(("attach", hwnd))

    def open_media(self, media_path: str) -> None:
        self.media_path = media_path
        self.calls.append(("open", media_path))

    def play(self) -> None:
        self.calls.append(("play", None))

    def pause(self) -> None:
        self.calls.append(("pause", None))

    def stop(self) -> None:
        self.calls.append(("stop", None))

    def update_viewpoint(self, viewpoint: VlcViewpoint) -> None:
        self.viewpoint = viewpoint
        self.calls.append(("viewpoint", viewpoint))


def test_validate_vlc_dir_requires_expected_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="libvlc.dll"):
        validate_vlc_dir(tmp_path)

    (tmp_path / "libvlc.dll").write_text("", encoding="utf-8")
    (tmp_path / "plugins").mkdir()

    assert validate_vlc_dir(tmp_path) == tmp_path


def test_controller_open_media_updates_config_and_starts_playback() -> None:
    backend = FakeBackend()
    controller = VlcPlayerController(backend, VlcPlayerConfig(auto_play=True))

    updated = controller.open_media(r"D:\video\movie.mp4")

    assert updated.last_media == r"D:\video\movie.mp4"
    assert backend.calls == [("open", r"D:\video\movie.mp4"), ("play", None)]


def test_controller_open_media_preserves_original_path_when_vlc_uses_prepared_copy() -> None:
    backend = FakeBackend()
    controller = VlcPlayerController(backend, VlcPlayerConfig(auto_play=False))

    updated = controller.open_media(r"D:\video\movie.mp4", vlc_media_path=r"E:\cache\movie.mp4")

    assert updated.last_media == r"D:\video\movie.mp4"
    assert backend.calls == [("open", r"E:\cache\movie.mp4")]


def test_prepare_media_path_returns_original_when_injection_is_disabled(tmp_path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"not-an-mp4")
    config = VlcPlayerConfig(serve_spherical_metadata=False)

    assert _prepare_media_path_for_vlc(str(media), config) == str(media)


def test_prepare_media_path_returns_virtual_http_url_when_metadata_is_enabled(tmp_path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(
        b"\x00\x00\x00\x0cftypisom"
        b"\x00\x00\x00\x08moov"
        b"\x00\x00\x00\x08mdat"
    )
    server = VirtualMp4Server()
    try:
        config = VlcPlayerConfig(serve_spherical_metadata=True)

        url = _prepare_media_path_for_vlc(str(media), config, server)

        assert url.startswith("http://127.0.0.1:")
    finally:
        server.stop()


def test_media_prepare_thread_posts_ready_message_without_opening_on_caller_thread(tmp_path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"not-an-mp4")
    messages: Queue[PlayerMessage] = Queue()
    config = VlcPlayerConfig(serve_spherical_metadata=False)

    thread = _start_media_prepare_thread(str(media), config, messages, VirtualMp4Server())
    thread.join(timeout=2)

    message = messages.get_nowait()
    assert message.kind == "media_ready"
    assert message.media_path == str(media)
    assert message.vlc_media_path == str(media)


def test_controller_updates_viewpoint_from_relative_ypr() -> None:
    backend = FakeBackend()
    controller = VlcPlayerController(
        backend,
        VlcPlayerConfig(
            gain_yaw=2.0,
            gain_pitch=1.0,
            deadzone_degrees=0.1,
            field_of_view=70.0,
            smoothing_alpha=1.0,
            max_step_degrees=999.0,
            max_yaw_degrees=180.0,
            max_pitch_degrees=90.0,
        ),
    )

    controller.update_pose((5.0, -3.0, 1.0))

    assert backend.viewpoint == VlcViewpoint(yaw=-10.0, pitch=3.0, roll=1.0, field_of_view=70.0)


def test_controller_reset_pose_control_recenters_viewpoint() -> None:
    backend = FakeBackend()
    controller = VlcPlayerController(
        backend,
        VlcPlayerConfig(
            smoothing_alpha=0.25,
            max_step_degrees=3.0,
            max_yaw_degrees=90.0,
            max_pitch_degrees=45.0,
        ),
    )

    controller.update_pose((40.0, 0.0, 0.0))
    controller.reset_pose_control()
    controller.update_pose((0.0, 0.0, 0.0))

    assert backend.viewpoint == VlcViewpoint(yaw=0.0, pitch=0.0, roll=0.0, field_of_view=80.0)


def test_controller_playback_methods_delegate_to_backend() -> None:
    backend = FakeBackend()
    controller = VlcPlayerController(backend, VlcPlayerConfig())

    controller.play()
    controller.pause()
    controller.stop()

    assert backend.calls == [("play", None), ("pause", None), ("stop", None)]


def test_relative_ypr_wraps_yaw_across_180_boundary() -> None:
    assert _relative_ypr((-179.0, 5.0, 2.0), (179.0, 1.0, -1.0)) == (
        2.0,
        4.0,
        3.0,
    )
