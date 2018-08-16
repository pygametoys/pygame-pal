from __future__ import (
    division,
    absolute_import,
    print_function,
    unicode_literals
)
import os
import sys
import six
try:
    import pygame as pg
except ImportError:
    # import pygame_sdl2 as pg
    # pg.import_as_pygame()
    raise RuntimeError("pygame is not installed")

from pygame.compat import xrange_ as range
try:
    from itertools import izip as zip
except ImportError:
    from builtins import zip

try:
    import textwrap3 as textwrap
except ImportError:
    import textwrap

try:
    from functools import partialmethod, lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache
    from backports.functools_partialmethod import partialmethod

from pgpal import config


FileNotFoundError = getattr(six.moves.builtins, 'FileNotFountError', IOError)


def open_ignore_case(filepath, *args, **kwargs):
    if not os.path.isabs(filepath):
        filepath = os.path.join(config['game_path'], filepath)
    filedir, filename = os.path.split(filepath)
    for name in {filename, filename.capitalize(),
                 filename.upper(), filename.lower()}:
        test_path = os.path.join(filedir, name)
        if os.path.exists(test_path):
            return open(test_path, *args, **kwargs)
    else:
        if 'w' in args[0]:
            return open(filepath, *args, **kwargs)
        raise FileNotFoundError
