from __future__ import annotations

import os
import sys
from collections.abc import Iterator, MutableMapping
from io import BytesIO
from pathlib import Path
from typing import Any

from configobj import ConfigObj
from configobj.validate import Validator

_SPEC = BytesIO(
    b"""
fps = integer(default=10)
battle_fps = integer(default=25)
volume = integer(0, 100, default=100)
full_screen = boolean(default=False)
use_embedded_font = boolean(default=False)
use_iso_font = boolean(default=False)
font_file = string(default='wqy-unibit.pcf')
msg_file = string(default='')
opl_samplerate = integer(0, 49716, default=49716)
samplerate = integer(0, 49716, default=44100)
cd = option('mp3', 'ogg', '', default='')
music_type = option('midi', 'mp3', 'ogg', 'rix', 'wav', default='rix')
midi_port = string(default='')
midi_backend = option('rtmidi', 'pygame', 'portmidi', 'amidi', 'supriya', default='supriya')
window_height = integer(default=400)
window_width = integer(default=640)
enable_joystick = boolean(default=False)
enable_mouse = boolean(default=False)
enable_avi_play = boolean(default=True)
enable_music = boolean(default=True)
enable_sound = boolean(default=True)
show_console = boolean(default=False)
game_path = string(default='.')
opl_chip = option('opl2', 'opl3', default='opl2')
"""
)

vdt = Validator()
configspec = ConfigObj(_SPEC, encoding="UTF8", list_values=False, _inspec=True)

_CONFIG: ConfigObj | None = None


def configure_environment() -> None:
    if sys.platform.startswith("win"):
        os.environ.setdefault("SDL_VIDEODRIVER", "windib")


def build_config(path: str | os.PathLike[str] | None = None) -> ConfigObj:
    cfg_path = Path(path or "pgpal.cfg").resolve()
    config = ConfigObj(str(cfg_path), configspec=configspec)
    config.validate(vdt)
    return config


def load_config(
    path: str | os.PathLike[str] | None = None,
    *,
    force: bool = False,
) -> ConfigObj:
    global _CONFIG
    if _CONFIG is None or force:
        _CONFIG = build_config(path)
    return _CONFIG


def initialize_runtime(
    path: str | os.PathLike[str] | None = None,
    *,
    force: bool = False,
) -> ConfigObj:
    configure_environment()
    return load_config(path, force=force)


def is_config_loaded() -> bool:
    return _CONFIG is not None


class ConfigProxy(MutableMapping[str, Any]):
    def _config(self) -> ConfigObj:
        return load_config()

    def __getitem__(self, key: str) -> Any:
        return self._config()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._config()[key] = value

    def __delitem__(self, key: str) -> None:
        del self._config()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._config())

    def __len__(self) -> int:
        return len(self._config())

    def __getattr__(self, name: str) -> Any:
        return getattr(self._config(), name)

    def __repr__(self) -> str:
        return repr(self._config()) if is_config_loaded() else "<ConfigProxy unloaded>"


config = ConfigProxy()
