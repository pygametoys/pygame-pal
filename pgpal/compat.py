from __future__ import (
    division,
    absolute_import,
    print_function,
    unicode_literals
)
import os

try:
    import cwcwidth as wcwidth  # noqa: F401
except ImportError:
    import wcwidth  # noqa: F401


from pgpal import config


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
        mode = kwargs.get('mode', args[0] if len(args) else '')
        if 'w' in mode:
            return open(filepath, *args, **kwargs)
        raise FileNotFoundError

def error_box(message):
    title = 'Fatal error'
    import platform
    system = platform.system()
    try:
        if system == 'Windows':
            MB_ICONERROR = 0x10
            MB_OK = 0
            from ctypes import windll
            windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONERROR)
        else:
            from subprocess import call
            if system == 'Linux':
                call(['zenity', '--error', '--title', repr(title), '--text', repr(message)])
            elif system == 'Darwin':
                call(['/Applications/CocoaDialog.app/Contents/MacOS/CocoaDialog', 'ok-msgbox', '--icon', 'x', '--title', repr(title), '--text', repr(message)])
            else:
                raise Exception()
    except Exception:
        import logging
        logging.error(message)
