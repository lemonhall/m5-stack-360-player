from __future__ import annotations

import struct
from urllib.request import Request, urlopen

from pc_receiver.mp4_spherical_metadata import inject_equirectangular_metadata
from pc_receiver.virtual_mp4_server import (
    VirtualMp4Server,
    build_equirectangular_virtual_mp4,
)


def _box(name: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, name) + payload


def _hdlr(handler_type: bytes) -> bytes:
    return _box(b"hdlr", b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + handler_type + b"\x00" * 8)


def _stco(offset: int) -> bytes:
    payload = b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">I", offset)
    return _box(b"stco", payload)


def _sample_mp4() -> bytes:
    video_trak = _box(
        b"trak",
        _box(b"mdia", _hdlr(b"vide") + _box(b"minf", _box(b"stbl", _stco(100)))),
    )
    return (
        _box(b"ftyp", b"isom\x00\x00\x00\x01")
        + _box(b"moov", video_trak)
        + _box(b"mdat", b"0123456789abcdef")
        + b"\x0b\x0b"
    )


def test_virtual_mp4_bytes_match_physical_metadata_injection(tmp_path) -> None:
    source = tmp_path / "sample.mp4"
    source.write_bytes(_sample_mp4())
    physical = tmp_path / "physical.mp4"
    inject_equirectangular_metadata(source, physical)

    virtual = build_equirectangular_virtual_mp4(source)

    assert virtual.size == physical.stat().st_size
    assert virtual.read_range(0, virtual.size - 1) == physical.read_bytes()


def test_virtual_mp4_server_serves_range_without_cache_file(tmp_path) -> None:
    source = tmp_path / "sample.mp4"
    source.write_bytes(_sample_mp4())
    server = VirtualMp4Server()
    server.start()
    try:
        url = server.add_media(source)
        request = Request(url, headers={"Range": "bytes=0-31"})

        with urlopen(request, timeout=5) as response:
            payload = response.read()
            content_range = response.headers["Content-Range"]

        assert response.status == 206
        assert content_range.startswith("bytes 0-31/")
        assert payload == build_equirectangular_virtual_mp4(source).read_range(0, 31)
        assert not list(tmp_path.glob("*.spherical.mp4"))
    finally:
        server.stop()


def test_virtual_mp4_server_supports_head_and_full_get(tmp_path) -> None:
    source = tmp_path / "sample.mp4"
    source.write_bytes(_sample_mp4())
    server = VirtualMp4Server()
    server.start()
    try:
        url = server.add_media(source)
        virtual = build_equirectangular_virtual_mp4(source)

        head_request = Request(url, method="HEAD")
        with urlopen(head_request, timeout=5) as response:
            assert response.status == 200
            assert int(response.headers["Content-Length"]) == virtual.size
            assert response.headers["Accept-Ranges"] == "bytes"

        with urlopen(url, timeout=5) as response:
            payload = response.read()

        assert response.status == 200
        assert payload == virtual.read_range(0, virtual.size - 1)
    finally:
        server.stop()
