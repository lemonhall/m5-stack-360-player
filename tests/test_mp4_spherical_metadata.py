from __future__ import annotations

import struct

from pc_receiver.mp4_spherical_metadata import (
    SPHERICAL_UUID_ID,
    inject_equirectangular_metadata,
    spherical_uuid_box,
)


def _box(name: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, name) + payload


def _hdlr(handler_type: bytes) -> bytes:
    return _box(b"hdlr", b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + handler_type + b"\x00" * 8)


def _stco(offset: int) -> bytes:
    payload = b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">I", offset)
    return _box(b"stco", payload)


def _read_stco_offset(payload: bytes) -> int:
    index = payload.index(b"stco")
    content_start = index + 4
    return struct.unpack(">I", payload[content_start + 8 : content_start + 12])[0]


def test_spherical_uuid_box_declares_equirectangular_projection() -> None:
    payload = spherical_uuid_box()

    assert SPHERICAL_UUID_ID in payload
    assert b"<GSpherical:ProjectionType>equirectangular</GSpherical:ProjectionType>" in payload


def test_inject_file_writes_spherical_metadata_and_updates_stco_when_moov_precedes_mdat(
    tmp_path,
) -> None:
    source = tmp_path / "sample.mp4"
    output = tmp_path / "output.mp4"
    video_trak = _box(
        b"trak",
        _box(b"mdia", _hdlr(b"vide") + _box(b"minf", _box(b"stbl", _stco(200)))),
    )
    audio_trak = _box(b"trak", _box(b"mdia", _hdlr(b"soun")))
    source.write_bytes(
        _box(b"ftyp", b"isom\x00\x00\x00\x01")
        + _box(b"moov", video_trak + audio_trak)
        + _box(b"mdat", b"\x00" * 32)
    )

    inject_equirectangular_metadata(source, output)
    payload = output.read_bytes()

    assert SPHERICAL_UUID_ID in payload
    assert payload.count(SPHERICAL_UUID_ID) == 1
    assert _read_stco_offset(payload) == 200 + len(spherical_uuid_box())


def test_inject_file_ignores_short_top_level_trailing_padding(tmp_path) -> None:
    source = tmp_path / "sample.mp4"
    output = tmp_path / "output.mp4"
    video_trak = _box(b"trak", _box(b"mdia", _hdlr(b"vide")))
    source.write_bytes(
        _box(b"ftyp", b"isom")
        + _box(b"moov", video_trak)
        + _box(b"mdat", b"")
        + (b"\x0b" * 11)
    )

    inject_equirectangular_metadata(source, output)
    payload = output.read_bytes()

    assert SPHERICAL_UUID_ID in payload
    assert payload.endswith(b"\x0b" * 11)
