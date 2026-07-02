# ECN-0002: Inject Equirectangular Metadata for VLC

## Basic Information

- **ECN ID**: ECN-0002
- **Related PRD**: PRD-0002
- **Related Req IDs**: REQ-0002-002, REQ-0002-003, REQ-0002-004
- **Discovery phase**: v2 real media verification
- **Date**: 2026-07-02

## Change Reason

The real local VR files are 2:1 HEVC MP4 files that PotPlayer can play correctly when its 360 menu is set to `Equirectangular`. `ffprobe` shows the sample does not carry spherical metadata, so VLC auto-detection may render the frame as a normal flat video unless projection is forced.

The previous diagnosis that this required switching away from VLC was wrong. The target remains embedded VLC/libVLC.

## Change Content

### Original Design

VLC was allowed to auto-detect whether a media file should use 360 projection.

### New Design

The VLC player defaults to creating or reusing a cached MP4 copy with Google spherical metadata declaring equirectangular projection. This is exposed as `inject_spherical_metadata` and `metadata_cache_dir` in `config/local.vlc-player.json`, plus a GUI checkbox, defaulting to enabled.

## Impact

- Affected Req IDs: REQ-0002-002, REQ-0002-003, REQ-0002-004
- Affected v2 plan: `docs/plan/v2-index.md`, `docs/plan/v2-vlc-player.md`
- Affected tests: `tests/test_mp4_spherical_metadata.py`, `tests/test_vlc_player_config.py`, `tests/test_vlc_player_controller.py`
- Affected code: `pc_receiver/mp4_spherical_metadata.py`, `pc_receiver/vlc_player_config.py`, `pc_receiver/vlc_player_app.py`

## Disposition

- [x] PRD updated
- [x] v2 plan updated
- [x] Tests updated
- [x] README updated
