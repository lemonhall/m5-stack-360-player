from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ble_runtime_is_pinned_to_python_313() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13"

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["requires-python"] == ">=3.13,<3.14"


def test_console_script_project_is_packaged() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["m5-visualizer"] == (
        "pc_receiver.visualizer_app:main"
    )
    assert pyproject["project"]["scripts"]["m5-vlc-player"] == (
        "pc_receiver.vlc_player_app:main"
    )
    assert "python-vlc>=3.0.21203" in pyproject["project"]["optional-dependencies"]["player"]
    assert "bleak>=0.22.3" in pyproject["project"]["optional-dependencies"]["player"]
    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "pc_receiver*"
    ]


def test_local_player_config_is_gitignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "config/local.*.json" in gitignore
