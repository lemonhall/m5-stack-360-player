from __future__ import annotations

from dataclasses import replace

from pc_receiver.vlc_backend import VlcBackend
from pc_receiver.vlc_player_config import VlcPlayerConfig
from pc_receiver.vlc_viewpoint import ViewpointSettings, map_ypr_to_viewpoint
from pc_receiver.telemetry import Vector3


class VlcPlayerController:
    def __init__(self, backend: VlcBackend, config: VlcPlayerConfig) -> None:
        self.backend = backend
        self.config = config

    def attach_to_window(self, hwnd: int) -> None:
        self.backend.attach_to_window(hwnd)

    def open_media(self, media_path: str) -> VlcPlayerConfig:
        self.backend.open_media(media_path)
        self.config = replace(self.config, last_media=media_path)
        if self.config.auto_play:
            self.backend.play()
        return self.config

    def play(self) -> None:
        self.backend.play()

    def pause(self) -> None:
        self.backend.pause()

    def stop(self) -> None:
        self.backend.stop()

    def update_pose(self, relative_ypr: Vector3) -> None:
        viewpoint = map_ypr_to_viewpoint(
            relative_ypr,
            ViewpointSettings(
                gain_yaw=self.config.gain_yaw,
                gain_pitch=self.config.gain_pitch,
                deadzone_degrees=self.config.deadzone_degrees,
                field_of_view=self.config.field_of_view,
            ),
        )
        self.backend.update_viewpoint(viewpoint)
