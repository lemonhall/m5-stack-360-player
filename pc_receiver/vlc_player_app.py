from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Literal

from pc_receiver.app import DEFAULT_CHARACTERISTIC_UUID
from pc_receiver.mp4_spherical_metadata import ensure_equirectangular_metadata_copy
from pc_receiver.telemetry import TelemetryError, Vector3, parse_telemetry
from pc_receiver.transport import iter_ble_notifications
from pc_receiver.vlc_backend import LibVlcBackend, VlcBackend, validate_vlc_dir
from pc_receiver.vlc_player_config import DEFAULT_CONFIG_PATH, VlcPlayerConfig, load_config, save_config
from pc_receiver.vlc_viewpoint import ViewpointSettings, map_ypr_to_viewpoint


MessageKind = Literal["status", "pose", "error"]


class PlayerMessage:
    def __init__(
        self,
        kind: MessageKind,
        *,
        text: str = "",
        ypr: Vector3 | None = None,
        center_request: bool = False,
    ) -> None:
        self.kind = kind
        self.text = text
        self.ypr = ypr
        self.center_request = center_request


class VlcPlayerController:
    def __init__(self, backend: VlcBackend, config: VlcPlayerConfig) -> None:
        self.backend = backend
        self.config = config

    def attach_to_window(self, hwnd: int) -> None:
        self.backend.attach_to_window(hwnd)

    def open_media(self, media_path: str, *, vlc_media_path: str | None = None) -> VlcPlayerConfig:
        self.backend.open_media(media_path if vlc_media_path is None else vlc_media_path)
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


class VlcPlayerWindow:
    def __init__(self, root: tk.Tk, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)
        self.messages: Queue[PlayerMessage] = Queue()
        self.stop_event = Event()
        self.ble_thread: Thread | None = None
        self.backend: LibVlcBackend | None = None
        self.controller: VlcPlayerController | None = None
        self.center_ypr: Vector3 | None = None
        self.latest_ypr: Vector3 | None = None

        root.title("M5 VLC 360 Player")
        root.geometry("1100x720")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.vlc_dir_var = tk.StringVar(value=self.config.vlc_dir)
        self.ble_address_var = tk.StringVar(value=self.config.ble_address)
        self.media_var = tk.StringVar(value=self.config.last_media)
        self.gain_yaw_var = tk.StringVar(value=str(self.config.gain_yaw))
        self.gain_pitch_var = tk.StringVar(value=str(self.config.gain_pitch))
        self.deadzone_var = tk.StringVar(value=str(self.config.deadzone_degrees))
        self.fov_var = tk.StringVar(value=str(self.config.field_of_view))
        self.inject_metadata_var = tk.BooleanVar(value=self.config.inject_spherical_metadata)
        self.metadata_cache_var = tk.StringVar(value=self.config.metadata_cache_dir)
        self.status_var = tk.StringVar(value="ready")
        self.pose_var = tk.StringVar(value="ypr=(0.0, 0.0, 0.0)")

        self._build_layout()
        self._init_backend()
        self._poll_messages()

    def _build_layout(self) -> None:
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        tk.Button(top, text="打开视频", command=self.open_media_dialog).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="播放", command=self.play).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="暂停", command=self.pause).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="停止", command=self.stop).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="连接 M5", command=self.connect_ble).pack(side=tk.LEFT, padx=12)
        tk.Button(top, text="校准", command=self.calibrate).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="保存配置", command=self.save_settings).pack(side=tk.LEFT, padx=12)

        settings = tk.Frame(self.root)
        settings.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        self._entry(settings, "VLC", self.vlc_dir_var, 34)
        self._entry(settings, "BLE", self.ble_address_var, 18)
        self._entry(settings, "Yaw", self.gain_yaw_var, 5)
        self._entry(settings, "Pitch", self.gain_pitch_var, 5)
        self._entry(settings, "Deadzone", self.deadzone_var, 5)
        self._entry(settings, "FOV", self.fov_var, 5)
        tk.Checkbutton(settings, text="Inject 360", variable=self.inject_metadata_var).pack(
            side=tk.LEFT, padx=(10, 2)
        )

        media_row = tk.Frame(self.root)
        media_row.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        tk.Label(media_row, text="媒体").pack(side=tk.LEFT)
        tk.Entry(media_row, textvariable=self.media_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        tk.Label(media_row, text="缓存").pack(side=tk.LEFT, padx=(8, 2))
        tk.Entry(media_row, textvariable=self.metadata_cache_var, width=22).pack(side=tk.LEFT)

        self.video_frame = tk.Frame(self.root, background="black")
        self.video_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=8)

        bottom = tk.Frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        tk.Label(bottom, textvariable=self.status_var, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(bottom, textvariable=self.pose_var, anchor=tk.E).pack(side=tk.RIGHT)

    def _entry(self, parent: tk.Frame, label: str, variable: tk.StringVar, width: int) -> None:
        tk.Label(parent, text=label).pack(side=tk.LEFT, padx=(8, 2))
        tk.Entry(parent, textvariable=variable, width=width).pack(side=tk.LEFT)

    def _init_backend(self) -> None:
        try:
            validate_vlc_dir(self.config.vlc_dir)
            self.backend = LibVlcBackend(self.config.vlc_dir)
            self.controller = VlcPlayerController(self.backend, self.config)
            self.root.update_idletasks()
            self.controller.attach_to_window(self.video_frame.winfo_id())
            self.status_var.set("VLC ready")
        except Exception as exc:
            self.status_var.set(f"VLC error: {exc}")

    def open_media_dialog(self) -> None:
        filename = filedialog.askopenfilename(
            title="打开 360 视频",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm"),
                ("All files", "*.*"),
            ],
            initialfile=self.media_var.get(),
        )
        if filename:
            self.open_media(filename)

    def open_media(self, media_path: str) -> None:
        if self.controller is None:
            messagebox.showerror("VLC unavailable", self.status_var.get())
            return
        self.config = self._config_from_fields(last_media=media_path)
        self.controller.config = self.config
        try:
            vlc_media_path = _prepare_media_path_for_vlc(media_path, self.config)
        except Exception as exc:
            messagebox.showerror("media prepare failed", str(exc))
            self.status_var.set(f"media prepare error: {exc}")
            return
        self.controller.open_media(media_path, vlc_media_path=vlc_media_path)
        self.media_var.set(media_path)
        save_config(self.config, self.config_path)
        suffix = " via spherical cache" if vlc_media_path != media_path else ""
        self.status_var.set(f"opened {Path(media_path).name}{suffix}")

    def play(self) -> None:
        if self.controller is not None:
            self.controller.play()
            self.status_var.set("playing")

    def pause(self) -> None:
        if self.controller is not None:
            self.controller.pause()
            self.status_var.set("paused")

    def stop(self) -> None:
        if self.controller is not None:
            self.controller.stop()
            self.status_var.set("stopped")

    def connect_ble(self) -> None:
        if self.ble_thread is not None and self.ble_thread.is_alive():
            self.status_var.set("BLE already connected")
            return
        self.config = self._config_from_fields()
        save_config(self.config, self.config_path)
        self.stop_event.clear()
        self.ble_thread = _start_ble_thread(
            self.config.ble_address,
            DEFAULT_CHARACTERISTIC_UUID,
            self.messages,
            self.stop_event,
        )
        self.status_var.set("BLE connecting")

    def calibrate(self) -> None:
        if self.latest_ypr is None:
            self.status_var.set("cannot calibrate before first M5 packet")
            return
        self.center_ypr = self.latest_ypr
        self.status_var.set("center calibrated")

    def save_settings(self) -> None:
        self.config = self._config_from_fields(last_media=self.media_var.get())
        save_config(self.config, self.config_path)
        self.status_var.set(f"saved {self.config_path}")

    def close(self) -> None:
        self.stop_event.set()
        if self.controller is not None:
            self.controller.stop()
        self.root.destroy()

    def _poll_messages(self) -> None:
        while True:
            try:
                message = self.messages.get_nowait()
            except Empty:
                break
            self._handle_message(message)
        if not self.stop_event.is_set():
            self.root.after(30, self._poll_messages)

    def _handle_message(self, message: PlayerMessage) -> None:
        if message.kind == "status":
            self.status_var.set(message.text)
        elif message.kind == "error":
            self.status_var.set(f"BLE error: {message.text}")
        elif message.kind == "pose" and message.ypr is not None:
            self.latest_ypr = message.ypr
            if message.center_request or self.center_ypr is None:
                self.center_ypr = message.ypr
            relative = _relative_ypr(message.ypr, self.center_ypr)
            self.pose_var.set(
                f"relative=({relative[0]:.1f}, {relative[1]:.1f}, {relative[2]:.1f})"
            )
            if self.controller is not None:
                self.config = self._config_from_fields(last_media=self.media_var.get())
                self.controller.config = self.config
                self.controller.update_pose(relative)

    def _config_from_fields(self, *, last_media: str | None = None) -> VlcPlayerConfig:
        return VlcPlayerConfig(
            vlc_dir=self.vlc_dir_var.get().strip(),
            ble_address=self.ble_address_var.get().strip(),
            last_media=self.media_var.get().strip() if last_media is None else last_media,
            gain_yaw=float(self.gain_yaw_var.get()),
            gain_pitch=float(self.gain_pitch_var.get()),
            deadzone_degrees=float(self.deadzone_var.get()),
            field_of_view=float(self.fov_var.get()),
            inject_spherical_metadata=bool(self.inject_metadata_var.get()),
            metadata_cache_dir=self.metadata_cache_var.get().strip(),
            auto_connect_ble=False,
            auto_play=False,
        )


async def _receive_loop(
    address: str,
    characteristic_uuid: str,
    messages: Queue[PlayerMessage],
    stop_event: Event,
) -> None:
    messages.put(PlayerMessage("status", text="BLE connecting"))
    try:
        async for raw in iter_ble_notifications(address, characteristic_uuid):
            if stop_event.is_set():
                return
            try:
                packet = parse_telemetry(raw)
            except TelemetryError:
                messages.put(PlayerMessage("status", text="BLE parse error"))
                continue
            if packet.ypr is None:
                continue
            messages.put(PlayerMessage("pose", ypr=packet.ypr, center_request=packet.btn))
    except Exception as exc:
        messages.put(PlayerMessage("error", text=str(exc)))
        print(f"VLC player BLE error: {exc}", file=sys.stderr, flush=True)


def _start_ble_thread(
    address: str,
    characteristic_uuid: str,
    messages: Queue[PlayerMessage],
    stop_event: Event,
) -> Thread:
    def target() -> None:
        asyncio.run(_receive_loop(address, characteristic_uuid, messages, stop_event))

    thread = Thread(target=target, name="m5-vlc-player-ble", daemon=True)
    thread.start()
    return thread


def _relative_ypr(current: Vector3, center: Vector3 | None) -> Vector3:
    if center is None:
        return current
    return (
        _wrap_degrees(current[0] - center[0]),
        current[1] - center[1],
        current[2] - center[2],
    )


def _wrap_degrees(value: float) -> float:
    while value <= -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value


def _prepare_media_path_for_vlc(media_path: str, config: VlcPlayerConfig) -> str:
    if not config.inject_spherical_metadata:
        return media_path
    return str(ensure_equirectangular_metadata_copy(media_path, config.metadata_cache_dir))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M5-controlled VLC 360 player")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="local JSON config path",
    )
    args = parser.parse_args(argv)

    root = tk.Tk()
    VlcPlayerWindow(root, Path(args.config))
    root.mainloop()
    return 0
