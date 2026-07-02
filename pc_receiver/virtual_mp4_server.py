from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import posixpath
from threading import Thread
from collections.abc import Iterator
from typing import BinaryIO
from urllib.parse import quote, urlparse
from uuid import uuid4

from pc_receiver import mp4_spherical_metadata as mp4


@dataclass(frozen=True)
class VirtualSegment:
    start: int
    size: int
    data: bytes | None = None
    source_offset: int | None = None

    @property
    def end_exclusive(self) -> int:
        return self.start + self.size


class VirtualMp4:
    def __init__(self, source_path: Path, segments: list[VirtualSegment]) -> None:
        self.source_path = source_path
        self.segments = segments
        self.size = 0 if not segments else segments[-1].end_exclusive

    def read_range(self, start: int, end: int) -> bytes:
        if start < 0 or end < start or end >= self.size:
            raise ValueError("invalid virtual MP4 range")
        chunks: list[bytes] = []
        chunks.extend(self.iter_range(start, end))
        return b"".join(chunks)

    def iter_range(self, start: int, end: int, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        if start < 0 or end < start or end >= self.size:
            raise ValueError("invalid virtual MP4 range")
        with self.source_path.open("rb") as src:
            for segment in self.segments:
                if segment.end_exclusive <= start:
                    continue
                if segment.start > end:
                    break
                local_start = max(start, segment.start) - segment.start
                local_end = min(end + 1, segment.end_exclusive) - segment.start
                yield from _iter_segment(src, segment, local_start, local_end, chunk_size)


def build_equirectangular_virtual_mp4(source_path: str | Path) -> VirtualMp4:
    source = Path(source_path)
    with source.open("rb") as src:
        atoms = mp4._parse_children(src, 0, source.stat().st_size, allow_trailing_junk=True)
        for atom in atoms:
            mp4._mark_video_tracks(src, atom)

        moov = next((atom for atom in atoms if atom.name == b"moov"), None)
        first_mdat = next((atom for atom in atoms if atom.name == b"mdat"), None)
        moov_delta = 0 if moov is None else moov.new_size() - moov.size
        chunk_offset_delta = (
            moov_delta
            if moov is not None and first_mdat is not None and moov.offset < first_mdat.offset
            else 0
        )

        segments: list[VirtualSegment] = []
        logical_offset = 0
        for atom in atoms:
            if first_mdat is not None and atom.offset >= first_mdat.offset:
                segments.append(
                    VirtualSegment(
                        start=logical_offset,
                        size=atom.size,
                        source_offset=atom.offset,
                    )
                )
                logical_offset += atom.size
                continue

            rendered = _render_atom(src, atom, chunk_offset_delta)
            segments.append(VirtualSegment(start=logical_offset, size=len(rendered), data=rendered))
            logical_offset += len(rendered)

    return VirtualMp4(source, segments)


class VirtualMp4Server:
    def __init__(self) -> None:
        self._media: dict[str, VirtualMp4] = {}
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._httpd is not None:
            return
        owner = self

        class Handler(_VirtualMp4Handler):
            media_owner = owner

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = Thread(target=self._httpd.serve_forever, name="m5-vlc-virtual-mp4", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._httpd = None
        self._thread = None
        self._media.clear()

    def add_media(self, media_path: str | Path) -> str:
        self.start()
        if self._httpd is None:
            raise RuntimeError("virtual MP4 server did not start")
        token = uuid4().hex
        self._media[token] = build_equirectangular_virtual_mp4(media_path)
        filename = quote(Path(media_path).name)
        host, port = self._httpd.server_address
        return f"http://{host}:{port}/{token}/{filename}"

    def get(self, token: str) -> VirtualMp4 | None:
        return self._media.get(token)


class _VirtualMp4Handler(BaseHTTPRequestHandler):
    media_owner: VirtualMp4Server
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._serve_media(send_body=True)

    def do_HEAD(self) -> None:
        self._serve_media(send_body=False)

    def _serve_media(self, *, send_body: bool) -> None:
        virtual = self._lookup_media()
        if virtual is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            start, end = _parse_range(self.headers.get("Range"), virtual.size)
        except ValueError:
            self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            return

        status = HTTPStatus.PARTIAL_CONTENT if self.headers.get("Range") else HTTPStatus.OK
        self.send_response(status)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(end - start + 1))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{virtual.size}")
        self.end_headers()
        if send_body:
            for chunk in virtual.iter_range(start, end):
                self.wfile.write(chunk)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _lookup_media(self) -> VirtualMp4 | None:
        parts = [part for part in posixpath.normpath(urlparse(self.path).path).split("/") if part]
        if not parts:
            return None
        return self.media_owner.get(parts[0])


def _parse_range(range_header: str | None, size: int) -> tuple[int, int]:
    if range_header is None:
        return 0, size - 1
    if not range_header.startswith("bytes="):
        raise ValueError("unsupported range unit")
    spec = range_header.removeprefix("bytes=").split(",", 1)[0].strip()
    start_text, end_text = spec.split("-", 1)
    if start_text == "":
        length = int(end_text)
        if length <= 0:
            raise ValueError("invalid suffix range")
        return max(0, size - length), size - 1
    start = int(start_text)
    end = size - 1 if end_text == "" else int(end_text)
    if start < 0 or end < start or start >= size:
        raise ValueError("invalid range")
    return start, min(end, size - 1)


def _render_atom(src: BinaryIO, atom: mp4.Atom, chunk_offset_delta: int) -> bytes:
    output = BytesIO()
    mp4._write_atom(src, output, atom, chunk_offset_delta)
    return output.getvalue()


def _read_segment(src: BinaryIO, segment: VirtualSegment, start: int, end: int) -> bytes:
    if segment.data is not None:
        return segment.data[start:end]
    if segment.source_offset is None:
        raise ValueError("file-backed segment missing source offset")
    src.seek(segment.source_offset + start)
    return src.read(end - start)


def _iter_segment(
    src: BinaryIO,
    segment: VirtualSegment,
    start: int,
    end: int,
    chunk_size: int,
) -> Iterator[bytes]:
    if segment.data is not None:
        offset = start
        while offset < end:
            next_offset = min(offset + chunk_size, end)
            yield segment.data[offset:next_offset]
            offset = next_offset
        return
    if segment.source_offset is None:
        raise ValueError("file-backed segment missing source offset")
    src.seek(segment.source_offset + start)
    remaining = end - start
    while remaining:
        chunk = src.read(min(chunk_size, remaining))
        if not chunk:
            raise ValueError("unexpected EOF while reading virtual MP4 segment")
        yield chunk
        remaining -= len(chunk)
