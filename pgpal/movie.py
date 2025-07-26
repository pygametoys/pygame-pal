#! /bin/env python
import os

from pgpal import config
import pygame as pg
from pgpal.const import *
from pgpal.mkfext import RNG
from pgpal.utils import adjust_pcm_volume


class MoviePlayerMixin(object):
    def __init__(self):
        self.rng = RNG()
        self.playing_rng = False

    def play_rng(self, index, start, end, speed):
        delay = int(800.0 / (speed or 16))
        self.rng.start_video(index, self.screen)
        self.rng.frame_index = start
        for i in range(start, end):
            till = pg.time.get_ticks() + delay
            self.rng.get_next_frame()
            self.update_screen()
            if self.need_fadein:
                self.fadein(1)
                self.need_fadein = False
            self.delay_until(till)
            if not self.rng.has_next_frame():
                break
        self.rng.finish_current_video()

    def play_video(self, avi_file):
        try:
            import numpy as np
            import sounddevice as sd
            from decord import AudioReader, VideoReader
            from decord import cpu

            class VideoReaderWrapper(VideoReader):
                """
                Used to fix a memory leak bug in decord.VideoReader
                Taken from here.
                https://github.com/dmlc/decord/issues/208#issuecomment-1157632702
                """
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.seek(0)
                    
                    self.path = args[0]

                def __getitem__(self, key):
                    frames = super().__getitem__(key)
                    self.seek(0)
                    return frames
        except ImportError:
            return False
        if not config['enable_avi_play']:
            return False
        avi_file = os.path.join(config['game_path'], avi_file)
        if os.path.exists(avi_file):
            self.screen_real = pg.display.set_mode(
                self.screen_real.get_size(),
                self.screen_real.get_flags(),
                32
            )
            ctx = cpu(0)
            audio_reader = AudioReader(avi_file, ctx, sample_rate=44100, mono=True)
            audio_reader.add_padding()
            video_reader = VideoReaderWrapper(avi_file, ctx)
            frame_count = len(video_reader)
            try:
                with sd.OutputStream(
                    samplerate=audio_reader.sample_rate,
                    channels=audio_reader.shape[0],
                ) as output:
                    prev_audio_end_idx = 0
                    for i in range(frame_count):
                        curtime = pg.time.get_ticks()
                        frame_start_time, frame_end_time = video_reader.get_frame_timestamp(i)
                        frame = video_reader[i].asnumpy()
                        size = self.screen_real.get_size()
                        audio_end_idx = audio_reader._time_to_sample(frame_end_time)
                        audio = audio_reader[prev_audio_end_idx:audio_end_idx].asnumpy().T
                        output.write(adjust_pcm_volume(audio))
                        self.screen_real.blit(
                            pg.transform.smoothscale(
                                pg.image.frombuffer(
                                    frame,
                                    (frame.shape[1], frame.shape[0]), 'RGB'
                                ), size
                            ), (0, 0)
                        )
                        pg.display.flip()
                        self.delay_until(curtime + int((frame_end_time - frame_start_time) * 1000))
                        if self.input_state.key_press:
                            raise KeyboardInterrupt
                        prev_audio_end_idx = audio_end_idx
            except KeyboardInterrupt:
                pass
            finally:
                self.clear_key_state()

            self.screen_real = pg.display.set_mode(
                self.screen_real.get_size(),
                self.screen_real.get_flags(),
                8
            )
            self.set_palette(self.num_palette, self.night_palette)
            return True
        else:
            return False
