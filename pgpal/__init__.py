#! /usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from configobj import ConfigObj
from validate import Validator
from io import BytesIO

if sys.platform.startswith('win'):
    os.environ['SDL_VIDEODRIVER'] = 'windib'

vdt = Validator()

spec = BytesIO(b'''
fps = integer(default=10)
battle_fps = integer(default=25)
volume = integer(0, 100, default=100)
full_screen = boolean(default=False)
use_embedded_font = boolean(default=False)
use_iso_font = boolean(default=False)
font_file = string(default='wqy-unibit.bdf')
msg_file = string(default='')
opl_samplerate = integer(0, 49716, default=49716)
samplerate = integer(0, 49716, default=44100)
cd = option('cd', 'mp3', 'ogg', '', default='')
music_type = option('midi', 'mp3', 'ogg', 'rix', 'wav', default='rix')
midi_port = string(default='')
midi_backend = option('rtmidi', 'pygame', 'portmidi', 'amidi', default='pygame')
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
''')

configspec = ConfigObj(spec, encoding='UTF8',
                       list_values=False, _inspec=True)
config = ConfigObj(os.path.abspath('pgpal.cfg'), configspec=configspec)
config.validate(vdt)
