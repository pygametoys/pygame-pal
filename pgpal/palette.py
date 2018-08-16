##! /usr/bin/env python
# -*- coding: UTF-8 -*-
import copy
from pgpal import config
from pgpal.compat import pg, range, open_ignore_case as open
from pgpal.const import FRAME_TIME, Direction
from pgpal.utils import pal_x, pal_y


class PalettePainterMixin(object):

    def __init__(self):
        self.shake_time = 0
        self.shake_level = 0
        self.num_palette = 0
        self.night_palette = False
        self.need_fadein = False
        offset = 0x28
        max_index = 11
        file_size = 0x300
        try:
            with open('pat.mkf', 'rb') as f:
                content = bytearray(f.read())

                # 新建一个数组保存11个调色板文件（每个调色板256种颜色）
                self.palettes = [
                    [
                        pg.Color(
                            *(x << 2 for x in content[pos:pos + 3])
                        ) for pos in range(
                            index, index + file_size, 3
                        )
                    ] for index in range(
                        offset,
                        offset + max_index * file_size, file_size
                    )
                ]
        except IOError:
            print('error occurs when try to open file pat.mkf')

    def get_palette(self, palette_num=None, night=None):
        if palette_num is None:
            palette_num = self.num_palette
        if night is None:
            night = self.night_palette
        if 0 < palette_num <= 5:
            palette_num += 1
        elif palette_num > 5:
            palette_num += 2
        if night and palette_num in {0, 6}:
            palette_num += 1
        return self.palettes[palette_num]

    def fadeout(self, delay):
        palette = self.screen.get_palette()
        self.fade(palette, delay, True)
        self.set_screen_palette([pg.Color(0, 0, 0) for _ in range(256)])

    def fade(self, palette, delay, out):
        t = pg.time.get_ticks() + delay * 600
        while True:
            j = int((t - pg.time.get_ticks()) / delay / 10)
            if j < 0:
                break
            if not out:
                j = 60 - j
            new_palette = [
                pg.Color(
                    (color.r * j) >> 6,
                    (color.g * j) >> 6,
                    (color.b * j) >> 6
                )
                for color in palette
            ]
            self.set_screen_palette(new_palette)
            self.delay(10)

    def fadein(self, delay, *args):
        palette = self.get_palette(*args)
        self.fade(palette, delay, False)
        self.set_screen_palette(palette)

    def set_palette(self, palette_num, night=False):
        palette = self.get_palette(palette_num, night)
        self.set_screen_palette(palette)

    def set_screen_palette(self, palette):
        if pg.get_sdl_version() >= (2, 0, 0):
            pass  # fixme?
        else:
            self.screen_real.set_palette(palette)
            self.screen.set_palette(palette)
            self.screen_bak.set_palette(palette)

    def palette_fade(self, update_scene, *args):
        new_palette = self.get_palette(*args)
        if new_palette is None:
            return
        palette = self.screen.get_palette()
        for i in range(32):
            if update_scene:
                ticks = pg.time.get_ticks() + FRAME_TIME
            else:
                ticks = (FRAME_TIME // 4)
            t = [
                pg.Color(
                    (palette[j].r * (31 - i) + new_palette[j].r * i) // 31,
                    (palette[j].g * (31 - i) + new_palette[j].g * i) // 31,
                    (palette[j].b * (31 - i) + new_palette[j].b * i) // 31,
                )
                for j in range(256)
            ]
            self.set_screen_palette(t)
            if update_scene:
                self.clear_key_state()
                self.input_state.curdir = Direction.Unknown
                self.input_state.prevdir = Direction.Unknown
                self.update(False)
                self.make_scene()
                self.update_screen()
            self.process_event()
            while pg.time.get_ticks() < ticks:
                self.process_event()
                pg.time.delay(5)

    def color_fade(self, delay, color, from_color):
        palette = self.get_palette()
        delay = (delay or 1) * 10
        if from_color:
            new_palette = [pg.Color(*palette[color])] * 256
            for i in range(64):
                for j in range(256):
                    if new_palette[j].r > palette[j].r:
                        new_palette[j].r -= 4
                    elif new_palette[j].r < palette[j].r:
                        new_palette[j].r += 4
                    if new_palette[j].g > palette[j].g:
                        new_palette[j].g -= 4
                    elif new_palette[j].g < palette[j].g:
                        new_palette[j].g += 4
                    if new_palette[j].b > palette[j].b:
                        new_palette[j].b -= 4
                    elif new_palette[j].b < palette[j].b:
                        new_palette[j].b += 4
                self.set_screen_palette(new_palette)
                self.delay(delay)
            self.set_screen_palette(palette)
        else:
            new_palette = copy.deepcopy(palette)
            for i in range(64):
                for j in range(256):
                    if new_palette[j].r > palette[color].r:
                        new_palette[j].r -= 4
                    elif new_palette[j].r < palette[color].r:
                        new_palette[j].r += 4
                    if new_palette[j].g > palette[color].g:
                        new_palette[j].g -= 4
                    elif new_palette[j].g < palette[color].g:
                        new_palette[j].g += 4
                    if new_palette[j].b > palette[color].b:
                        new_palette[j].b -= 4
                    elif new_palette[j].b < palette[color].b:
                        new_palette[j].b += 4
                self.set_screen_palette(new_palette)
                self.delay(delay)
            new_palette = [pg.Color(*palette[color])] * 256
            self.set_screen_palette(new_palette)

    def scene_fade(self, step, *args):
        palette = self.get_palette(*args)
        if palette is None:
            return
        if step == 0:
            step = 1
        self.need_to_fadein = False
        if step > 0:
            steps = range(0, 64, step)
        else:
            steps = range(63, -1, step)
        for i in steps:
            ticks = pg.time.get_ticks() + 100
            self.clear_key_state()
            self.input_state.curdir = Direction.Unknown
            self.input_state.prevdir = Direction.Unknown
            self.update(False)
            self.make_scene()
            self.update_screen()
            new_palette = [
                pg.Color(
                    (color.r * i) >> 6,
                    (color.g * i) >> 6,
                    (color.b * i) >> 6
                ) for color in palette
            ]
            self.set_screen_palette(new_palette)
            self.process_event()
            while pg.time.get_ticks() <= ticks:
                self.process_event()
                pg.time.delay(5)

    def fade_to_red(self):
        palette = self.get_palette()
        new_palette = copy.deepcopy(palette)
        pxarray = pg.PixelArray(self.screen)
        for x in range(self.screen.get_width()):
            for y in range(self.screen.get_height()):
                if pxarray[x, y] == 0x4F:
                    pxarray[x, y] = 0x4E
        del pxarray
        self.screen.unlock()
        self.update_screen()
        for _ in range(32):
            for j in range(256):
                if j == 0x4F:
                    continue
                color = (palette[j].r + palette[j].g + palette[j].b) // 4 + 64
                if new_palette[j].r > color:
                    new_palette[j].r -= min(new_palette[j].r - color, 8)
                elif new_palette[j].r < color:
                    new_palette[j].r += min(color - new_palette[j].r, 8)
                if new_palette[j].g > 0:
                    new_palette[j].g -= min(new_palette[j].g, 8)
                if new_palette[j].b > 0:
                    new_palette[j].b -= min(new_palette[j].b, 8)
            self.set_screen_palette(new_palette)
            self.delay(75)
