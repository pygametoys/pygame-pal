# -*- coding: utf8 -*-
from io import BytesIO
from threading import Thread
import wave

import pygame as pg
import sndhdr

from pgpal.mkfbase import MKFDecoder, is_win95
from pgpal import config


class Voice(Thread):
    def __init__(self, index, mkf):
        super().__init__(daemon=True)
        data = mkf.read(index, True)
        if len(data):
            if is_win95:
                self.io = BytesIO(data)
            else:
                self.io = BytesIO()
                wav = wave.open(self.io, 'wb')
                data = mkf.read(index, True)
                header = sndhdr.test_voc(data, 0)
                if header is not None:
                    rate = header[1]
                else:
                    rate = 11025
                wav.setparams((1, 1, rate, 0, 'NONE', "not compressed"))
                wav.writeframes(data[26:])
                wav.close()
                self.io.seek(0)
        else:
            self.io = None

    def run(self):
        if self.io is not None:
            sound = pg.mixer.Sound(self.io)
            sound.set_volume(config["volume"] / 100.0)
            sound.play()


class SoundEffectPlayerMixin(object):
    def __init__(self):
        self.sounds = MKFDecoder('sounds.mkf' if is_win95 else 'voc.mkf', yj1=False)

    def play_sound(self, index):
        if config['enable_sound']:
            Voice(abs(index), self.sounds).start()
