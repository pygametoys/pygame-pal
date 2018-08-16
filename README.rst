============
PyGame-Pal
============

.. image:: https://img.shields.io/badge/license-GPLv3-red.svg
.. image:: https://img.shields.io/badge/language-python-blue.svg
.. image:: https://img.shields.io/badge/python-2%20%7C%203-lightblue.svg
.. image:: https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20osx-purple.svg

A pygame-based open-source re-implemention of the classic Chinese RPG game `Chinese Paladin(仙剑奇侠传) <https://zh.wikipedia.org/wiki/%E4%BB%99%E5%89%91%E5%A5%87%E4%BE%A0%E4%BC%A0/>`_ .It is heavily based on the palresearch documents(http://github.com/palxex/palresearch),

the sdlpal project(http://github.com/sdlpal/sdlpal),

and huangcd's work(http://github.com/huangcd/python-pal).

CPython 2.6/2.7 and CPython 3.3+ versions are both supported(however, python3 is recommended), tested on Manjaro Linux 17.1 and Windows 7, 64bit.

Dependency:
___________
	| pygame (based on sdl 1.x)
	| six
	| chardet
	| configobj
	| attrs
	| wcwidth
	| wrapt
	| pyperclip
	| pyaudio (for rix music & sound effect playback)
	| mido (for midi music playback)

Python2 specific requirements:
______________________________
	| enum34
	| textwrap3
	| backports.functools_lru_cache
	| backports.functools_partialmethod

Optional requirements:
______________________
	| pyopl (based on dosbox opl synth, for opl music emulation. If you are using python 3.x, use this branch instead: https://github.com/pygametoys/pyopl/tree/pyopl-py3)
	| pyav (based on ffmpeg, for avi video playback)
	| ptpython (for a better repl)
	| psyco (only for CPython 2.x x86 versions to speed up a little bit)

Development requirements:
_________________________
	| cython (to build the c version yj1 decompress backend)

Features:
_________
    1. multi-threaded audio player

    2. an interactive console that can access the main game instance, like below

    .. image:: screenshot.png

    3. a too simple config program also based on pygame

    4. snake-case function names

    5. no need to re-compile after code modification

To-dos:
_______
    - Refactor some c-style code to python's style
    - Enhance the performance
    - Port more opl emulation cores?
    - Test if the joystick input works correctly or not
    - Fix potential bugs.

License:
________
    GPLv3
