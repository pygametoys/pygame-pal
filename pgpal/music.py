#! /usr/bin/env python
# -*- coding: utf8 -*-
from io import BytesIO
import os
from threading import Thread
import time
import mido
from pgpal.const import PAL_MAX_VOLUME
from pgpal.compat import pg, open_ignore_case as open, FileNotFoundError
from pgpal.mkfbase import MKFDecoder
from pgpal import config


class Midi(Thread):

    def __init__(self):
        Thread.__init__(self)
        mido.backends.backend.DEFAULT_BACKEND = 'mido.backends.%s' % (
            config['midi_backend']
        )
        avail_ports = mido.get_output_names()
        if config['midi_port'] and config['midi_port'] in avail_ports:
            self.port = mido.open_output(name=config['midi_port'])
        elif len(avail_ports):
            self.port = mido.open_output(name=avail_ports[0])

    def load(self, index):
        if os.path.exists('Musics'):
            try:
                name = open('./Musics/%.3d.mid' % index, 'rb')
                self.midifile = mido.MidiFile(file=name)
                return True
            except (FileNotFoundError, ValueError):
                self.midifile = mido.MidiFile()
                return False
        elif os.path.exists('midi.mkf'):
            data = MKFDecoder('midi.mkf', yj1=False).read(index, True)
            if len(data):
                name = BytesIO(data)
                self.midifile = mido.MidiFile(file=name)
                return True
            else:
                self.midifile = mido.MidiFile()
                return False
        else:
            self.midifile = mido.MidiFile()
            return False

    def play(self, loop=0):
        self.loop = loop
        self.unpause()

    def run(self):
        self.n = self.loop = 0
        self.paused = True
        while not self.port.closed:
            while not self.paused:
                _id = id(self.midifile)
                for msg in self.midifile.play():
                    if hasattr('msg', 'velocity'):
                        msg.velocity = msg.velocity * \
                           config['volume'] / PAL_MAX_VOLUME
                    self.port.send(msg)
                    if self.paused or _id != id(self.midifile):
                        break
                if not self.loop:
                    self.paused = True
                    self.port.send(mido.Message('stop'))
                    self.port.reset()
                    break
                if self.port.closed:
                    break
            with self.port._lock:
                if self.paused:
                    time.sleep(0.1)

    def pause(self):
        self.paused = True
        self.port.panic()
        self.port.reset()

    def unpause(self):
        self.paused = False

    def stop(self):
        self.loop = 0
        self.pause()

    def quit(self):
        self.stop()
        self.port.close()


class Music(object):
    @staticmethod
    def load(index):
        for ext in {'ogg', 'mp3', 'wav'}:
            name = './/{ext}/{num:02d}.{ext}'.format(ext=ext, num=index)
            path = os.path.join(config['game_path'], name)
            if os.path.exists(path):
                pg.mixer.music.load(path)
                return True
        else:
            return False

    unpause = staticmethod(pg.mixer.music.unpause)
    pause = staticmethod(pg.mixer.music.pause)
    play = staticmethod(pg.mixer.music.play)
    stop = staticmethod(pg.mixer.music.stop)
    fadeout = staticmethod(pg.mixer.music.fadeout)
    quit = staticmethod(pg.mixer.quit)


class FakeCD(Music):
    def __init__(self, fmt):
        self.fmt = fmt

    def play(self, track_id):
        name = './/{ext}/100{num:02d}.{ext}'.format(ext=self.fmt, num=track_id)
        path = os.path.join(config['game_path'], name)
        if os.path.exists(path):
            pg.mixer.music.load(path)
        else:
            return False
        pg.mixer.music.play(0)
        return True


class MusicPlayerMixin(object):
    def __init__(self):
        self.num_music = None
        self.num_battle_music = None
        if config['music_type'] == 'midi':
            self.music = Midi()
            self.music.start()
        elif config['music_type'] == 'rix':
            from pgpal.rix import Rix
            self.music = Rix()
        else:
            self.music = Music()
        cd = config['cd']
        if cd:
            if cd in {'ogg', 'mp3'}:
                self.cd = FakeCD(cd)
            elif hasattr(pg, 'cdrom') and pg.cdrom.get_count() > 0:
                self.cd = pg.cdrom.CD(cd)

    def play_music(self, index=None, loop=True, fade_time=0):
        if index is None:
            index = self.num_music
        loaded = self.music.load(index)
        if hasattr(self.music, 'fadeout'):
            self.music.fadeout(int(fade_time * 1000))
        else:
            self.stop_music()
        if config['enable_music'] and loaded:
            try:
                if loop:
                    self.music.play(-1)
                else:
                    self.music.play(0)
            except IOError:
                pass

    def play_cd_track(self, track_id):
        self.stop_music()
        if hasattr(self, 'cd') and config['enable_music']:
            return self.cd.play(track_id)
        else:
            return False

    def on_off_music(self, value):
        config['enable_music'] = value
        if value:
            self.unpause_music()
        else:
            self.pause_music()

    def unpause_music(self):
        self.music.unpause()

    def pause_music(self):
        self.music.pause()

    def stop_music(self):
        pg.mixer.music.stop()
        self.music.stop()

    def quit_music(self):
        if hasattr(self, 'cd'):
            self.cd.quit()
        self.music.quit()

    def set_volume(self, volume):
        config['volume'] = min(volume, PAL_MAX_VOLUME)
        pg.mixer.music.set_volume(volume)
