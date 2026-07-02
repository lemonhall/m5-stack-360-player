from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from pc_receiver.vlc_viewpoint import VlcViewpoint


class VlcBackend(Protocol):
    def attach_to_window(self, hwnd: int) -> None: ...
    def open_media(self, media_path: str) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...
    def get_time_ms(self) -> int: ...
    def get_length_ms(self) -> int: ...
    def set_time_ms(self, time_ms: int) -> None: ...
    def update_viewpoint(self, viewpoint: VlcViewpoint) -> None: ...


def validate_vlc_dir(vlc_dir: str | Path) -> Path:
    path = Path(vlc_dir)
    libvlc = path / "libvlc.dll"
    plugins = path / "plugins"
    if not libvlc.exists():
        raise FileNotFoundError(f"libvlc.dll not found: {libvlc}")
    if not plugins.exists():
        raise FileNotFoundError(f"VLC plugins directory not found: {plugins}")
    return path


class LibVlcBackend:
    def __init__(self, vlc_dir: str | Path) -> None:
        self.vlc_dir = validate_vlc_dir(vlc_dir)
        os.environ["PYTHON_VLC_LIB_PATH"] = str(self.vlc_dir / "libvlc.dll")
        os.environ["VLC_PLUGIN_PATH"] = str(self.vlc_dir / "plugins")
        os.add_dll_directory(str(self.vlc_dir))

        import vlc  # type: ignore[import-untyped]

        self._vlc = vlc
        self._instance = vlc.Instance()
        self._player = self._instance.media_player_new()
        self._viewpoint = vlc.libvlc_video_new_viewpoint()
        if not hasattr(vlc.MediaPlayer, "video_update_viewpoint"):
            raise RuntimeError("libVLC does not expose video_update_viewpoint")

    def attach_to_window(self, hwnd: int) -> None:
        self._player.set_hwnd(hwnd)

    def open_media(self, media_path: str) -> None:
        media = self._instance.media_new(media_path)
        self._player.set_media(media)

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def get_time_ms(self) -> int:
        return max(0, int(self._player.get_time()))

    def get_length_ms(self) -> int:
        return max(0, int(self._player.get_length()))

    def set_time_ms(self, time_ms: int) -> None:
        self._player.set_time(max(0, int(time_ms)))

    def update_viewpoint(self, viewpoint: VlcViewpoint) -> None:
        target = self._viewpoint.contents
        target.yaw = viewpoint.yaw
        target.pitch = viewpoint.pitch
        target.roll = viewpoint.roll
        target.field_of_view = viewpoint.field_of_view
        self._player.video_update_viewpoint(self._viewpoint, True)


def probe_vlc_viewpoint_api(vlc_dir: str | Path) -> bool:
    path = validate_vlc_dir(vlc_dir)
    os.environ["PYTHON_VLC_LIB_PATH"] = str(path / "libvlc.dll")
    os.environ["VLC_PLUGIN_PATH"] = str(path / "plugins")
    os.add_dll_directory(str(path))

    import vlc  # type: ignore[import-untyped]

    return hasattr(vlc.MediaPlayer, "video_update_viewpoint") and hasattr(
        vlc, "libvlc_video_new_viewpoint"
    )
