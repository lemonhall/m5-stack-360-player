from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import BinaryIO


SPHERICAL_UUID_ID = bytes.fromhex("ffcc8263f8554a938814587a02521fdd")

SPHERICAL_XML = b"""<?xml version="1.0"?>
<rdf:SphericalVideo xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:GSpherical="http://ns.google.com/videos/1.0/spherical/">
  <GSpherical:Spherical>true</GSpherical:Spherical>
  <GSpherical:Stitched>true</GSpherical:Stitched>
  <GSpherical:StitchingSoftware>M5Stack 360 Player</GSpherical:StitchingSoftware>
  <GSpherical:ProjectionType>equirectangular</GSpherical:ProjectionType>
</rdf:SphericalVideo>
"""

CONTAINER_TYPES = {b"moov", b"trak", b"mdia", b"minf", b"stbl"}


@dataclass
class Atom:
    offset: int
    size: int
    name: bytes
    header_size: int
    children: list["Atom"] | None = None
    inject_spherical: bool = False
    trailing: bool = False

    @property
    def content_offset(self) -> int:
        return self.offset + self.header_size

    @property
    def end_offset(self) -> int:
        return self.offset + self.size

    def new_size(self) -> int:
        if self.trailing:
            return self.size
        if self.children is None:
            return self.size
        total = self.header_size + sum(child.new_size() for child in self.children)
        if self.inject_spherical:
            total += len(spherical_uuid_box())
        return total


def spherical_uuid_box() -> bytes:
    payload = SPHERICAL_UUID_ID + SPHERICAL_XML
    return struct.pack(">I4s", len(payload) + 8, b"uuid") + payload


def inject_equirectangular_metadata(source: str | Path, output: str | Path) -> None:
    source_path = Path(source)
    output_path = Path(output)
    with source_path.open("rb") as src:
        file_size = source_path.stat().st_size
        atoms = _parse_children(src, 0, file_size, allow_trailing_junk=True)
        for atom in atoms:
            _mark_video_tracks(src, atom)

        moov = next((atom for atom in atoms if atom.name == b"moov"), None)
        first_mdat = next((atom for atom in atoms if atom.name == b"mdat"), None)
        moov_delta = 0 if moov is None else moov.new_size() - moov.size
        chunk_offset_delta = (
            moov_delta
            if moov is not None and first_mdat is not None and moov.offset < first_mdat.offset
            else 0
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as dst:
            for atom in atoms:
                _write_atom(src, dst, atom, chunk_offset_delta)


def _parse_children(
    src: BinaryIO, start: int, limit: int, *, allow_trailing_junk: bool = False
) -> list[Atom]:
    children: list[Atom] = []
    offset = start
    while offset + 8 <= limit:
        try:
            atom = _parse_atom(src, offset, limit)
        except ValueError:
            if allow_trailing_junk:
                children.append(
                    Atom(
                        offset=offset,
                        size=limit - offset,
                        name=b"tail",
                        header_size=0,
                        trailing=True,
                    )
                )
                return children
            raise
        children.append(atom)
        offset = atom.end_offset
    if allow_trailing_junk and offset < limit:
        children.append(
            Atom(
                offset=offset,
                size=limit - offset,
                name=b"tail",
                header_size=0,
                trailing=True,
            )
        )
    return children


def _parse_atom(src: BinaryIO, offset: int, limit: int) -> Atom:
    src.seek(offset)
    header = src.read(8)
    if len(header) != 8:
        raise ValueError(f"truncated MP4 atom header at offset {offset}")
    size32, name = struct.unpack(">I4s", header)
    header_size = 8
    if size32 == 1:
        largesize = src.read(8)
        if len(largesize) != 8:
            raise ValueError(f"truncated MP4 large-size atom at offset {offset}")
        size = struct.unpack(">Q", largesize)[0]
        header_size = 16
    elif size32 == 0:
        size = limit - offset
    else:
        size = size32
    if size < header_size or offset + size > limit:
        raise ValueError(f"invalid MP4 atom {name!r} at offset {offset}")

    atom = Atom(offset=offset, size=size, name=name, header_size=header_size)
    if name in CONTAINER_TYPES:
        atom.children = _parse_children(src, atom.content_offset, atom.end_offset)
    return atom


def _mark_video_tracks(src: BinaryIO, atom: Atom) -> None:
    if atom.children is None:
        return
    for child in atom.children:
        _mark_video_tracks(src, child)
    if atom.name == b"trak" and _is_video_track(src, atom):
        atom.inject_spherical = True


def _is_video_track(src: BinaryIO, trak: Atom) -> bool:
    mdia = _first_child(trak, b"mdia")
    hdlr = None if mdia is None else _first_child(mdia, b"hdlr")
    if hdlr is None:
        return False
    src.seek(hdlr.content_offset + 8)
    return src.read(4) == b"vide"


def _first_child(atom: Atom, name: bytes) -> Atom | None:
    if atom.children is None:
        return None
    return next((child for child in atom.children if child.name == name), None)


def _write_atom(src: BinaryIO, dst: BinaryIO, atom: Atom, chunk_offset_delta: int) -> None:
    if atom.trailing:
        _copy_range(src, dst, atom.offset, atom.size)
        return
    if atom.children is None:
        if atom.name == b"stco" and chunk_offset_delta:
            _write_stco(src, dst, atom, chunk_offset_delta)
        elif atom.name == b"co64" and chunk_offset_delta:
            _write_co64(src, dst, atom, chunk_offset_delta)
        else:
            _copy_range(src, dst, atom.offset, atom.size)
        return

    _write_atom_header(dst, atom.name, atom.new_size())
    for child in atom.children:
        _write_atom(src, dst, child, chunk_offset_delta)
    if atom.inject_spherical:
        dst.write(spherical_uuid_box())


def _write_atom_header(dst: BinaryIO, name: bytes, size: int) -> None:
    if size <= 0xFFFFFFFF:
        dst.write(struct.pack(">I4s", size, name))
    else:
        dst.write(struct.pack(">I4sQ", 1, name, size))


def _write_stco(src: BinaryIO, dst: BinaryIO, atom: Atom, delta: int) -> None:
    src.seek(atom.content_offset)
    payload = bytearray(src.read(atom.size - atom.header_size))
    count = struct.unpack(">I", payload[4:8])[0]
    for index in range(count):
        entry_offset = 8 + index * 4
        value = struct.unpack(">I", payload[entry_offset : entry_offset + 4])[0]
        payload[entry_offset : entry_offset + 4] = struct.pack(">I", value + delta)
    _write_atom_header(dst, atom.name, atom.size)
    dst.write(payload)


def _write_co64(src: BinaryIO, dst: BinaryIO, atom: Atom, delta: int) -> None:
    src.seek(atom.content_offset)
    payload = bytearray(src.read(atom.size - atom.header_size))
    count = struct.unpack(">I", payload[4:8])[0]
    for index in range(count):
        entry_offset = 8 + index * 8
        value = struct.unpack(">Q", payload[entry_offset : entry_offset + 8])[0]
        payload[entry_offset : entry_offset + 8] = struct.pack(">Q", value + delta)
    _write_atom_header(dst, atom.name, atom.size)
    dst.write(payload)


def _copy_range(src: BinaryIO, dst: BinaryIO, offset: int, size: int) -> None:
    src.seek(offset)
    remaining = size
    while remaining:
        chunk = src.read(min(1024 * 1024, remaining))
        if not chunk:
            raise ValueError("unexpected EOF while copying MP4 atom")
        dst.write(chunk)
        remaining -= len(chunk)
