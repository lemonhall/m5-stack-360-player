from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from queue import Empty, Queue
import sys
from threading import Event, Thread
import tkinter as tk
from typing import Literal

from pc_receiver.app import DEFAULT_CHARACTERISTIC_UUID
from pc_receiver.calibration import CalibrationState
from pc_receiver.telemetry import TelemetryError, Vector3, parse_telemetry
from pc_receiver.transport import iter_ble_notifications
from pc_receiver.visualization import CuboidModel, project_points, rotation_matrix_from_ypr, transform_points


MessageKind = Literal["snapshot", "status", "error"]


@dataclass(frozen=True)
class VisualizerSnapshot:
    seq: int
    absolute_ypr: Vector3
    display_ypr: Vector3
    centered: bool
    center_updated: bool


@dataclass(frozen=True)
class VisualizerMessage:
    kind: MessageKind
    text: str = ""
    snapshot: VisualizerSnapshot | None = None


class TkVisualizer:
    def __init__(
        self,
        root: tk.Tk,
        messages: Queue[VisualizerMessage],
        stop_event: Event,
        *,
        width: int = 900,
        height: int = 640,
    ) -> None:
        self.root = root
        self.messages = messages
        self.stop_event = stop_event
        self.model = CuboidModel.stick()
        self.snapshot: VisualizerSnapshot | None = None
        self.status = "waiting"
        self.width = width
        self.height = height

        root.title("M5StickC Plus2 Head Tracker")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.canvas = tk.Canvas(
            root,
            width=width,
            height=height,
            background="#111318",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

    def start(self) -> None:
        self._tick()
        self.root.mainloop()

    def close(self) -> None:
        self.stop_event.set()
        self.root.destroy()

    def _on_resize(self, event: tk.Event) -> None:
        self.width = int(event.width)
        self.height = int(event.height)
        self._draw()

    def _tick(self) -> None:
        self._drain_messages()
        self._draw()
        if not self.stop_event.is_set():
            self.root.after(33, self._tick)

    def _drain_messages(self) -> None:
        while True:
            try:
                message = self.messages.get_nowait()
            except Empty:
                return
            if message.kind == "snapshot" and message.snapshot is not None:
                self.snapshot = message.snapshot
                center = " centered" if message.snapshot.center_updated else ""
                self.status = f"seq={message.snapshot.seq}{center}"
            elif message.kind == "status":
                self.status = message.text
            elif message.kind == "error":
                self.status = f"error: {message.text}"

    def _draw(self) -> None:
        self.canvas.delete("all")
        self._draw_background()
        self._draw_axes()
        ypr = self.snapshot.display_ypr if self.snapshot is not None else (0.0, 0.0, 0.0)
        self._draw_stick(ypr)
        self._draw_status(ypr)

    def _draw_background(self) -> None:
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#111318", outline="")
        self.canvas.create_oval(
            self.width * 0.24,
            self.height * 0.24,
            self.width * 0.76,
            self.height * 0.76,
            outline="#252a33",
            width=1,
        )

    def _draw_axes(self) -> None:
        axis_points = ((0.0, 0.0, 0.0), (1.6, 0.0, 0.0), (0.0, 1.6, 0.0), (0.0, 0.0, 1.6))
        projected = project_points(axis_points, width=self.width, height=self.height, scale=52.0)
        origin = projected[0]
        axes = ((projected[1], "#e05c5c", "X"), (projected[2], "#56b870", "Y"), (projected[3], "#5b8def", "Z"))
        for endpoint, color, label in axes:
            self.canvas.create_line(origin[0], origin[1], endpoint[0], endpoint[1], fill=color, width=2)
            self.canvas.create_text(endpoint[0], endpoint[1], text=label, fill=color, font=("Segoe UI", 10, "bold"))

    def _draw_stick(self, ypr: Vector3) -> None:
        points = transform_points(self.model.vertices, rotation_matrix_from_ypr(ypr))
        projected = project_points(points, width=self.width, height=self.height)

        def face_depth(face: tuple[int, int, int, int]) -> float:
            return sum(points[index][2] for index in face) / len(face)

        for face in sorted(self.model.faces, key=face_depth):
            coords: list[float] = []
            for index in face:
                coords.extend(projected[index])
            self.canvas.create_polygon(coords, fill="#d68124", outline="#ffb347", width=1)

        for start, end in self.model.edges:
            p0 = projected[start]
            p1 = projected[end]
            self.canvas.create_line(p0[0], p0[1], p1[0], p1[1], fill="#ffd08a", width=2)

        nose = projected[1]
        self.canvas.create_oval(nose[0] - 6, nose[1] - 6, nose[0] + 6, nose[1] + 6, fill="#fff2b0", outline="")

    def _draw_status(self, ypr: Vector3) -> None:
        mode = "relative" if self.snapshot is not None and self.snapshot.centered else "absolute"
        text = f"{self.status}  {mode} ypr=({ypr[0]:.1f}, {ypr[1]:.1f}, {ypr[2]:.1f})"
        self.canvas.create_text(18, 18, text=text, fill="#dce2ea", anchor=tk.NW, font=("Segoe UI", 11))


async def _receive_loop(
    address: str,
    characteristic_uuid: str,
    messages: Queue[VisualizerMessage],
    stop_event: Event,
) -> None:
    state = CalibrationState()
    parse_errors = 0
    messages.put(VisualizerMessage(kind="status", text="connecting"))
    try:
        async for raw in iter_ble_notifications(address, characteristic_uuid):
            if stop_event.is_set():
                return
            try:
                packet = parse_telemetry(raw)
            except TelemetryError:
                parse_errors += 1
                messages.put(VisualizerMessage(kind="status", text=f"parse errors={parse_errors}"))
                continue
            view = state.update(packet)
            if view.absolute_ypr is None:
                continue
            snapshot = VisualizerSnapshot(
                seq=view.seq,
                absolute_ypr=view.absolute_ypr,
                display_ypr=view.relative_ypr if view.relative_ypr is not None else view.absolute_ypr,
                centered=view.relative_ypr is not None,
                center_updated=view.center_updated,
            )
            messages.put(VisualizerMessage(kind="snapshot", snapshot=snapshot))
    except Exception as exc:
        messages.put(VisualizerMessage(kind="error", text=str(exc)))
        print(f"visualizer BLE error: {exc}", file=sys.stderr, flush=True)


def _start_ble_thread(
    address: str,
    characteristic_uuid: str,
    messages: Queue[VisualizerMessage],
    stop_event: Event,
) -> Thread:
    def target() -> None:
        asyncio.run(_receive_loop(address, characteristic_uuid, messages, stop_event))

    thread = Thread(target=target, name="m5-visualizer-ble", daemon=True)
    thread.start()
    return thread


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visualize M5StickC Plus2 BLE telemetry")
    parser.add_argument("--address", required=True, help="BLE device address")
    parser.add_argument(
        "--characteristic",
        default=DEFAULT_CHARACTERISTIC_UUID,
        help="BLE telemetry characteristic UUID",
    )
    parser.add_argument("--width", type=int, default=900, help="initial window width")
    parser.add_argument("--height", type=int, default=640, help="initial window height")
    args = parser.parse_args(argv)

    messages: Queue[VisualizerMessage] = Queue()
    stop_event = Event()
    _start_ble_thread(args.address, args.characteristic, messages, stop_event)

    root = tk.Tk()
    visualizer = TkVisualizer(root, messages, stop_event, width=args.width, height=args.height)
    visualizer.start()
    return 0
