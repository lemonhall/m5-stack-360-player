from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Literal

from pc_receiver.app import DEFAULT_CHARACTERISTIC_UUID
from pc_receiver.pose_control import (
    AxisName,
    PoseControlSettings,
    PoseController,
    learn_axis_mapping_with_magnitude,
    map_control_axes,
)
from pc_receiver.telemetry import TelemetryError, Vector3, parse_telemetry
from pc_receiver.transport import iter_ble_notifications
from pc_receiver.virtual_mp4_server import VirtualMp4Server
from pc_receiver.vlc_backend import LibVlcBackend, VlcBackend, validate_vlc_dir
from pc_receiver.vlc_player_config import DEFAULT_CONFIG_PATH, VlcPlayerConfig, load_config, save_config
from pc_receiver.vlc_viewpoint import ViewpointSettings, map_ypr_to_viewpoint


MessageKind = Literal["status", "pose", "error", "media_ready", "media_prepare_error"]


class PlayerMessage:
    def __init__(
        self,
        kind: MessageKind,
        *,
        text: str = "",
        ypr: Vector3 | None = None,
        center_request: bool = False,
        media_path: str = "",
        vlc_media_path: str = "",
    ) -> None:
        self.kind = kind
        self.text = text
        self.ypr = ypr
        self.center_request = center_request
        self.media_path = media_path
        self.vlc_media_path = vlc_media_path


class VlcPlayerController:
    def __init__(self, backend: VlcBackend, config: VlcPlayerConfig) -> None:
        self.backend = backend
        self.config = config
        self.pose_controller = _build_pose_controller(config)
        self.pose_target: Vector3 | None = None

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

    def get_playback_position(self) -> tuple[int, int]:
        return self.backend.get_time_ms(), self.backend.get_length_ms()

    def seek_relative_seconds(self, seconds: int) -> None:
        current_ms, length_ms = self.get_playback_position()
        self.seek_to_ms(current_ms + seconds * 1000, length_ms=length_ms)

    def seek_to_fraction(self, fraction: float) -> None:
        _, length_ms = self.get_playback_position()
        if length_ms <= 0:
            return
        self.seek_to_ms(round(length_ms * _clamp_float(fraction, 0.0, 1.0)), length_ms=length_ms)

    def seek_to_ms(self, target_ms: int, *, length_ms: int | None = None) -> None:
        if length_ms is None:
            length_ms = self.backend.get_length_ms()
        if length_ms > 0:
            target_ms = min(length_ms, target_ms)
        self.backend.set_time_ms(max(0, int(target_ms)))

    def set_pose_target(self, relative_ypr: Vector3) -> None:
        self.pose_target = relative_ypr

    def render_pose_frame(self) -> None:
        if self.pose_target is None:
            return
        if self.pose_controller.settings != _pose_control_settings(self.config):
            self.pose_controller = _build_pose_controller(self.config)
        controlled_ypr = self.pose_controller.update(self.pose_target)
        viewpoint = map_ypr_to_viewpoint(
            controlled_ypr,
            ViewpointSettings(
                gain_yaw=self.config.gain_yaw,
                gain_pitch=self.config.gain_pitch,
                deadzone_degrees=self.config.deadzone_degrees,
                field_of_view=self.config.field_of_view,
                front_yaw_degrees=self.config.front_yaw_degrees,
                front_pitch_degrees=self.config.front_pitch_degrees,
                min_yaw_degrees=0.0,
                max_yaw_degrees=180.0,
            ),
        )
        self.backend.update_viewpoint(viewpoint)

    def update_pose(self, relative_ypr: Vector3) -> None:
        self.set_pose_target(relative_ypr)
        self.render_pose_frame()

    def reset_pose_control(self) -> None:
        self.pose_controller = _build_pose_controller(self.config)
        self.pose_controller.reset()
        self.pose_target = (0.0, 0.0, 0.0)


class VlcPlayerWindow:
    def __init__(self, root: tk.Tk, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)
        self.messages: Queue[PlayerMessage] = Queue()
        self.stop_event = Event()
        self.ble_thread: Thread | None = None
        self.media_prepare_thread: Thread | None = None
        self.virtual_mp4_server = VirtualMp4Server()
        self.backend: LibVlcBackend | None = None
        self.controller: VlcPlayerController | None = None
        self.center_ypr: Vector3 | None = None
        self.latest_ypr: Vector3 | None = None
        self.learning_motion: Literal["yaw", "pitch"] | None = None
        self.learning_start_ypr: Vector3 | None = None

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
        self.max_yaw_var = tk.StringVar(value=str(self.config.max_yaw_degrees))
        self.max_pitch_var = tk.StringVar(value=str(self.config.max_pitch_degrees))
        self.front_yaw_var = tk.StringVar(value=str(self.config.front_yaw_degrees))
        self.front_pitch_var = tk.StringVar(value=str(self.config.front_pitch_degrees))
        self.smoothing_var = tk.StringVar(value=str(self.config.smoothing_alpha))
        self.max_step_var = tk.StringVar(value=str(self.config.max_step_degrees))
        self.yaw_source_axis_var = tk.StringVar(value=self.config.yaw_source_axis)
        self.yaw_source_sign_var = tk.StringVar(value=str(self.config.yaw_source_sign))
        self.pitch_source_axis_var = tk.StringVar(value=self.config.pitch_source_axis)
        self.pitch_source_sign_var = tk.StringVar(value=str(self.config.pitch_source_sign))
        self.serve_metadata_var = tk.BooleanVar(value=self.config.serve_spherical_metadata)
        self.status_var = tk.StringVar(value="ready")
        self.pose_var = tk.StringVar(value="ypr=(0.0, 0.0, 0.0)")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.time_var = tk.StringVar(value="00:00 / 00:00")
        self.updating_progress = False

        self._build_layout()
        self._init_backend()
        root.bind_all("<Left>", self.on_left_key)
        root.bind_all("<Right>", self.on_right_key)
        self._poll_messages()
        self._poll_playback()
        self._poll_pose_control()

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
        self._entry(settings, "MaxYaw", self.max_yaw_var, 5)
        self._entry(settings, "MaxPitch", self.max_pitch_var, 5)
        self._entry(settings, "Smooth", self.smoothing_var, 5)
        self._entry(settings, "Step", self.max_step_var, 5)
        tk.Checkbutton(settings, text="360 metadata", variable=self.serve_metadata_var).pack(
            side=tk.LEFT, padx=(10, 2)
        )

        mapping = tk.Frame(self.root)
        mapping.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        self._entry(mapping, "FrontYaw", self.front_yaw_var, 5)
        self._entry(mapping, "FrontPitch", self.front_pitch_var, 5)
        self._axis_picker(mapping, "YawAxis", self.yaw_source_axis_var)
        self._entry(mapping, "YawSign", self.yaw_source_sign_var, 4)
        self._axis_picker(mapping, "PitchAxis", self.pitch_source_axis_var)
        self._entry(mapping, "PitchSign", self.pitch_source_sign_var, 4)
        tk.Button(mapping, text="学习左转", command=lambda: self.start_motion_learning("yaw")).pack(
            side=tk.LEFT, padx=(12, 3)
        )
        tk.Button(mapping, text="学习抬头", command=lambda: self.start_motion_learning("pitch")).pack(
            side=tk.LEFT, padx=3
        )

        media_row = tk.Frame(self.root)
        media_row.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        tk.Label(media_row, text="媒体").pack(side=tk.LEFT)
        tk.Entry(media_row, textvariable=self.media_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self.video_container = tk.Frame(self.root, background="black")
        self.video_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.video_frame = tk.Frame(self.video_container, background="black")
        self.video_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self.control_bar = tk.Frame(self.video_container, background="#111111", height=48)
        self.control_bar.place(relx=0.0, rely=1.0, relwidth=1.0, anchor=tk.SW)
        tk.Button(self.control_bar, text="-10s", command=lambda: self.seek_relative(-10)).pack(
            side=tk.LEFT, padx=(8, 3), pady=8
        )
        tk.Button(self.control_bar, text="播放", command=self.play).pack(side=tk.LEFT, padx=3, pady=8)
        tk.Button(self.control_bar, text="暂停", command=self.pause).pack(side=tk.LEFT, padx=3, pady=8)
        tk.Button(self.control_bar, text="+10s", command=lambda: self.seek_relative(10)).pack(
            side=tk.LEFT, padx=3, pady=8
        )
        tk.Scale(
            self.control_bar,
            variable=self.progress_var,
            from_=0.0,
            to=1000.0,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=self.on_progress_changed,
            background="#111111",
            foreground="white",
            troughcolor="#3a3a3a",
            highlightthickness=0,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=4)
        tk.Label(
            self.control_bar,
            textvariable=self.time_var,
            width=15,
            anchor=tk.E,
            background="#111111",
            foreground="white",
        ).pack(side=tk.RIGHT, padx=(0, 8), pady=8)
        self.control_bar.lift()

        bottom = tk.Frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        tk.Label(bottom, textvariable=self.status_var, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(bottom, textvariable=self.pose_var, anchor=tk.E).pack(side=tk.RIGHT)

    def _entry(self, parent: tk.Frame, label: str, variable: tk.StringVar, width: int) -> None:
        tk.Label(parent, text=label).pack(side=tk.LEFT, padx=(8, 2))
        tk.Entry(parent, textvariable=variable, width=width).pack(side=tk.LEFT)

    def _axis_picker(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        tk.Label(parent, text=label).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Combobox(
            parent,
            textvariable=variable,
            values=("yaw", "pitch", "roll"),
            width=6,
            state="readonly",
        ).pack(side=tk.LEFT)

    def _init_backend(self) -> None:
        try:
            validate_vlc_dir(self.config.vlc_dir)
            self.backend = LibVlcBackend(self.config.vlc_dir)
            self.controller = VlcPlayerController(self.backend, self.config)
            self.root.update_idletasks()
            self.controller.attach_to_window(self.video_frame.winfo_id())
            self.control_bar.lift()
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
        self.media_var.set(media_path)
        save_config(self.config, self.config_path)
        self.status_var.set(f"preparing {Path(media_path).name}")
        self.media_prepare_thread = _start_media_prepare_thread(
            media_path,
            self.config,
            self.messages,
            self.virtual_mp4_server,
        )

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

    def seek_relative(self, seconds: int) -> None:
        if self.controller is not None:
            self.controller.seek_relative_seconds(seconds)
            self._refresh_playback_progress()

    def on_left_key(self, event: tk.Event) -> str | None:
        if _is_text_input(event.widget):
            return None
        self.seek_relative(-10)
        return "break"

    def on_right_key(self, event: tk.Event) -> str | None:
        if _is_text_input(event.widget):
            return None
        self.seek_relative(10)
        return "break"

    def on_progress_changed(self, value: str) -> None:
        if self.updating_progress or self.controller is None:
            return
        self.controller.seek_to_fraction(float(value) / 1000.0)
        self._refresh_playback_progress()

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
        if self.controller is not None:
            self.controller.reset_pose_control()
            self.controller.update_pose((0.0, 0.0, 0.0))
        self.status_var.set("center calibrated")

    def start_motion_learning(self, target: Literal["yaw", "pitch"]) -> None:
        if self.latest_ypr is None:
            self.status_var.set("cannot learn before first M5 packet")
            return
        self.learning_motion = target
        self.learning_start_ypr = self.latest_ypr
        label = "left turn" if target == "yaw" else "look up"
        self.status_var.set(f"learning {label}: move now")
        self.root.after(1500, self.finish_motion_learning)

    def finish_motion_learning(self) -> None:
        if self.learning_motion is None or self.learning_start_ypr is None or self.latest_ypr is None:
            return
        target = self.learning_motion
        axis, sign, magnitude = learn_axis_mapping_with_magnitude(
            self.learning_start_ypr,
            self.latest_ypr,
        )
        if magnitude < 3.0:
            self.status_var.set("motion too small to learn axis")
            self.learning_motion = None
            self.learning_start_ypr = None
            return
        if target == "yaw":
            self.yaw_source_axis_var.set(axis)
            self.yaw_source_sign_var.set(str(sign))
            self.status_var.set(f"learned left turn: YawAxis={axis} YawSign={sign:.0f}")
        else:
            self.pitch_source_axis_var.set(axis)
            self.pitch_source_sign_var.set(str(sign))
            self.status_var.set(f"learned look up: PitchAxis={axis} PitchSign={sign:.0f}")
        self.learning_motion = None
        self.learning_start_ypr = None
        if self.controller is not None:
            self.controller.reset_pose_control()

    def save_settings(self) -> None:
        self.config = self._config_from_fields(last_media=self.media_var.get())
        save_config(self.config, self.config_path)
        self.status_var.set(f"saved {self.config_path}")

    def close(self) -> None:
        self.stop_event.set()
        if self.controller is not None:
            self.controller.stop()
        self.virtual_mp4_server.stop()
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

    def _poll_playback(self) -> None:
        self._refresh_playback_progress()
        if not self.stop_event.is_set():
            self.root.after(500, self._poll_playback)

    def _poll_pose_control(self) -> None:
        if self.controller is not None:
            self.controller.render_pose_frame()
        if not self.stop_event.is_set():
            self.root.after(16, self._poll_pose_control)

    def _refresh_playback_progress(self) -> None:
        if self.controller is None:
            return
        current_ms, length_ms = self.controller.get_playback_position()
        self.time_var.set(f"{_format_ms(current_ms)} / {_format_ms(length_ms)}")
        self.updating_progress = True
        try:
            if length_ms > 0:
                self.progress_var.set((current_ms / length_ms) * 1000.0)
            else:
                self.progress_var.set(0.0)
        finally:
            self.updating_progress = False

    def _handle_message(self, message: PlayerMessage) -> None:
        if message.kind == "status":
            self.status_var.set(message.text)
        elif message.kind == "error":
            self.status_var.set(f"BLE error: {message.text}")
        elif message.kind == "media_prepare_error":
            messagebox.showerror("media prepare failed", message.text)
            self.status_var.set(f"media prepare error: {message.text}")
        elif message.kind == "media_ready":
            self._open_prepared_media(message.media_path, message.vlc_media_path)
        elif message.kind == "pose" and message.ypr is not None:
            self.latest_ypr = message.ypr
            if message.center_request or self.center_ypr is None:
                self.center_ypr = message.ypr
                if self.controller is not None:
                    self.controller.reset_pose_control()
            relative = _relative_ypr(message.ypr, self.center_ypr)
            self.config = self._config_from_fields(last_media=self.media_var.get())
            mapped = map_control_axes(relative, _pose_control_settings(self.config))
            self.pose_var.set(
                "relative="
                f"({relative[0]:.1f}, {relative[1]:.1f}, {relative[2]:.1f}) "
                f"mapped=({mapped[0]:.1f}, {mapped[1]:.1f})"
            )
            if self.controller is not None:
                self.controller.config = self.config
                self.controller.set_pose_target(relative)

    def _open_prepared_media(self, media_path: str, vlc_media_path: str) -> None:
        if self.controller is None:
            return
        self.controller.open_media(media_path, vlc_media_path=vlc_media_path)
        suffix = " via virtual 360 metadata" if vlc_media_path != media_path else ""
        self.status_var.set(f"opened {Path(media_path).name}{suffix}")

    def _config_from_fields(self, *, last_media: str | None = None) -> VlcPlayerConfig:
        return VlcPlayerConfig(
            vlc_dir=self.vlc_dir_var.get().strip(),
            ble_address=self.ble_address_var.get().strip(),
            last_media=self.media_var.get().strip() if last_media is None else last_media,
            gain_yaw=float(self.gain_yaw_var.get()),
            gain_pitch=float(self.gain_pitch_var.get()),
            deadzone_degrees=float(self.deadzone_var.get()),
            field_of_view=float(self.fov_var.get()),
            max_yaw_degrees=float(self.max_yaw_var.get()),
            max_pitch_degrees=float(self.max_pitch_var.get()),
            front_yaw_degrees=float(self.front_yaw_var.get()),
            front_pitch_degrees=float(self.front_pitch_var.get()),
            smoothing_alpha=float(self.smoothing_var.get()),
            max_step_degrees=float(self.max_step_var.get()),
            yaw_source_axis=_axis_from_field(self.yaw_source_axis_var.get()),
            yaw_source_sign=float(self.yaw_source_sign_var.get()),
            pitch_source_axis=_axis_from_field(self.pitch_source_axis_var.get()),
            pitch_source_sign=float(self.pitch_source_sign_var.get()),
            serve_spherical_metadata=bool(self.serve_metadata_var.get()),
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


def _start_media_prepare_thread(
    media_path: str,
    config: VlcPlayerConfig,
    messages: Queue[PlayerMessage],
    virtual_mp4_server: VirtualMp4Server,
) -> Thread:
    def target() -> None:
        try:
            vlc_media_path = _prepare_media_path_for_vlc(media_path, config, virtual_mp4_server)
        except Exception as exc:
            messages.put(PlayerMessage("media_prepare_error", text=str(exc)))
            return
        messages.put(
            PlayerMessage("media_ready", media_path=media_path, vlc_media_path=vlc_media_path)
        )

    thread = Thread(target=target, name="m5-vlc-player-media-prepare", daemon=True)
    thread.start()
    return thread


def _build_pose_controller(config: VlcPlayerConfig) -> PoseController:
    return PoseController(_pose_control_settings(config))


def _pose_control_settings(config: VlcPlayerConfig) -> PoseControlSettings:
    return PoseControlSettings(
        max_yaw_degrees=config.max_yaw_degrees,
        max_pitch_degrees=config.max_pitch_degrees,
        smoothing_alpha=config.smoothing_alpha,
        max_step_degrees=config.max_step_degrees,
        yaw_source_axis=_axis_from_field(config.yaw_source_axis),
        yaw_source_sign=config.yaw_source_sign,
        pitch_source_axis=_axis_from_field(config.pitch_source_axis),
        pitch_source_sign=config.pitch_source_sign,
    )


def _axis_from_field(value: str) -> AxisName:
    if value in ("yaw", "pitch", "roll"):
        return value
    return "yaw"


def _relative_ypr(current: Vector3, center: Vector3 | None) -> Vector3:
    if center is None:
        return current
    return (
        _wrap_degrees(current[0] - center[0]),
        _wrap_degrees(current[1] - center[1]),
        _wrap_degrees(current[2] - center[2]),
    )


def _wrap_degrees(value: float) -> float:
    while value <= -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _format_ms(value: int) -> str:
    total_seconds = max(0, int(value // 1000))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _is_text_input(widget: object) -> bool:
    if not hasattr(widget, "winfo_class"):
        return False
    return widget.winfo_class() in {"Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox"}


def _prepare_media_path_for_vlc(
    media_path: str,
    config: VlcPlayerConfig,
    virtual_mp4_server: VirtualMp4Server | None = None,
) -> str:
    if not config.serve_spherical_metadata:
        return media_path
    if virtual_mp4_server is None:
        virtual_mp4_server = VirtualMp4Server()
    return virtual_mp4_server.add_media(media_path)


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
