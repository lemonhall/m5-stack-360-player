from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from pc_receiver.telemetry import TelemetryPacket, Vector3


class JsonlRecorder:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file: TextIO | None = None

    def __enter__(self) -> JsonlRecorder:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8", newline="\n")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def write(
        self,
        packet: TelemetryPacket,
        *,
        relative_ypr: Vector3 | None,
        center_updated: bool,
    ) -> None:
        if self._file is None:
            raise RuntimeError("JsonlRecorder must be used as a context manager")
        record = packet.to_record()
        record["relative_ypr"] = list(relative_ypr) if relative_ypr is not None else None
        record["center_updated"] = center_updated
        self._file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        self._file.write("\n")
        self._file.flush()
