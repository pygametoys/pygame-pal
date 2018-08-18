# -*- coding: utf8 -*-
from io import BytesIO
import sndhdr
from struct import unpack_from, pack_into
from threading import Thread
import time
import wave
import pyaudio
from pgpal.mkfbase import MKFDecoder, is_win95
from pgpal import config


def adjust_pcm_volume(data):
    view = bytearray(data)
    fmt = '%dh' % (len(data) // 2)
    values = unpack_from(fmt, view)
    pack_into(
        fmt, view, 0,
        *(int(round(val * config['volume'] / 100.0)) for val in values)
    )
    return bytes(view)


class Voice(Thread):
    audio = pyaudio.PyAudio()
    def __init__(self, index, mkf):
        Thread.__init__(self, daemon=True)
        data = mkf.read(index, True)
        if len(data):
            if is_win95:
                io = BytesIO(data)
            else:
                io = BytesIO()
                wav = wave.open(io, 'wb')
                data = mkf.read(index, True)
                header = sndhdr.test_voc(data, 0)
                if header is not None:
                    rate = header[1]
                else:
                    rate = 11025
                wav.setparams((1, 1, rate, 0, 'NONE', "not compressed"))
                wav.writeframes(data[26:])
                wav.close()
                io.seek(0)
            self.wav = wave.open(io, 'rb')
        else:
            self.wav = None

    def run(self):
        if self.wav is not None:
            while not self.audio.get_host_api_count():
                time.sleep(0.05)
            stream = self.audio.open(
                format=self.audio.get_format_from_width(self.wav.getsampwidth()),
                channels=self.wav.getnchannels(),
                rate=self.wav.getframerate(),
                output=True,
                frames_per_buffer=256
            )
            stream.start_stream()
            data = True
            while data:
                data = self.wav.readframes(256)
                stream.write(adjust_pcm_volume(data))
            self.wav.close()
            time.sleep(0.05)
            stream.stop_stream()
            stream.close()


class SoundEffectPlayerMixin(object):
    def __init__(self):
        self.sounds = MKFDecoder('sounds.mkf' if is_win95 else 'voc.mkf', yj1=False)

    def play_sound(self, index):
        if config['enable_sound']:
            Voice(abs(index), self.sounds).start()
