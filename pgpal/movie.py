#! /bin/env python
import os
from io import BytesIO
import wave
from pgpal import config
from pgpal.compat import pg, range
from pgpal.const import *
from pgpal.mkfext import RNG
from pgpal.text import encoding


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
            import av
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
            video = av.open(
                avi_file,
                metadata_encoding=encoding,
                metadata_errors='replace'
            )
            astream = next(s for s in video.streams if s.type == 'audio')
            fw = BytesIO()
            wav = wave.open(fw, 'wb')
            resampler = av.AudioResampler(
                format=av.AudioFormat('s16').packed,
                layout='stereo',
                rate=config['samplerate'],
            )
            wav.setparams(
                (2, 2, config['samplerate'], 0, 'NONE', "not compressed")
            )
            for packet in video.demux(astream):
                for frame in packet.decode():
                    frame = resampler.resample(frame)
                    wav.writeframes(frame.planes[0].to_bytes())
            wav.close()
            fw.seek(0)
            pg.mixer.music.load(fw)

            video = av.open(
                avi_file,
                metadata_encoding=encoding,
                metadata_errors='replace'
            )
            vstream = next(s for s in video.streams if s.type == 'video')
            rate = int(round(1000 / vstream.rate))
            pg.mixer.music.play()
            self.clear_key_state()
            other = not hasattr(pg.image, 'frombuffer')

            try:
                for packet in video.demux(vstream):
                    for frame in packet.decode():
                        size = self.screen_real.get_size()
                        curtime = pg.time.get_ticks()
                        if other:
                            img_obj = BytesIO()
                            frame.to_image().save(img_obj, 'bmp')
                            img_obj.seek(0)
                            self.screen_real.blit(
                                pg.transform.smoothscale(
                                    pg.image.load(img_obj), size),
                                (0, 0)
                            )
                        else:
                            data = frame.to_rgb().planes[0].to_bytes()
                            self.screen_real.blit(
                                pg.transform.smoothscale(
                                    pg.image.frombuffer(
                                        data,
                                        (288, 180), 'RGB'
                                    ), size
                                ), (0, 0)
                            )
                        pg.display.flip()

                        self.delay_until(curtime + rate)
                        if self.input_state.key_press:
                            raise KeyboardInterrupt
            except KeyboardInterrupt:
                pass
            finally:
                self.clear_key_state()
                if pg.mixer.get_init():
                    pg.mixer.music.pause()

            self.screen_real = pg.display.set_mode(
                self.screen_real.get_size(),
                self.screen_real.get_flags(),
                8
            )
            self.set_palette(self.num_palette, self.night_palette)
            return True
        else:
            return False
