#! /usr/bin/env python
# -*- coding: utf8 -*-
import attr
from io import BytesIO
import base64
import math
from pgpal import config
from pgpal.compat import pg, range, partialmethod
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.utils import pal_x, pal_y


@attr.s(slots=True)
class ScreenLayout(object):
    equip_image_box = attr.ib(default=(8, 8))
    equip_role_list_box = attr.ib(default=(2, 95))
    equip_item_name = attr.ib(default=(5, 70))
    equip_item_amount = attr.ib(default=(51, 57))
    equip_labels = attr.ib(default=[(92, 11), (92, 33), (92, 55),
                                    (92, 77), (92, 99), (92, 121)])
    equip_names = attr.ib(default=[(130, 11), (130, 33), (130, 55),
                                   (130, 77), (130, 99), (130, 121)])
    equip_status_labels = attr.ib(default=[
        (226, 10), (226, 32), (226, 54), (226, 76), (226, 98)])
    equip_status_values = attr.ib(default=[
        (260, 14), (260, 36), (260, 58), (260, 80), (260, 102)])
    role_name = attr.ib(default=(110, 8))
    role_image = attr.ib(default=(110, 30))
    role_exp_label = attr.ib(default=(6, 6))
    role_level_label = attr.ib(default=(6, 32))
    role_hp_label = attr.ib(default=(6, 54))
    role_mp_label = attr.ib(default=(6, 76))
    role_status_labels = attr.ib(default=[
        (6, 98),   (6, 118),  (6, 138),  (6, 158),  (6, 178)])
    role_curr_exp = attr.ib(default=(58, 6))
    role_next_exp = attr.ib(default=(58, 15))
    role_exp_slash = attr.ib(default=(0, 0))
    role_level = attr.ib(default=(54, 35))
    role_cur_hp = attr.ib(default=(42, 56))
    role_max_hp = attr.ib(default=(63, 61))
    role_hp_slash = attr.ib(default=(65, 58))
    role_cur_mp = attr.ib(default=(42, 78))
    role_max_mp = attr.ib(default=(63, 83))
    role_mp_slash = attr.ib(default=(65, 80))
    role_status_values = attr.ib(default=[
        (42, 102), (42, 122), (42, 142), (42, 162), (42, 182)])
    role_equip_image_boxes = attr.ib(default=[
        (189, -1), (247, 39), (251, 101),
        (201, 133), (141, 141), (81, 125)
    ])
    role_equip_names = attr.ib(default=[
        (195, 38), (253, 78), (257, 140),
        (207, 172), (147, 180), (87, 164)
    ])
    role_poison_names = attr.ib(default=[
        (185, 58), (185, 76), (185, 94), (185, 112), (185, 130),
        (185, 148), (185, 166), (185, 184), (185, 184), (185, 184)
    ])
    extra_item_desc_lines = attr.ib(default=(0, 0))
    extra_magic_desc_lines = attr.ib(default=(0, 0)) 


class ScreenDisplayMixin(object):
    def __init__(self):
        self.screen_layout = ScreenLayout()
        pg.display.set_caption(
            'PyGame-Pal %s' % (
                'Win95' if is_win95 else 'DOS'
            )
        )
        mode = HWSURFACE | DOUBLEBUF | HWPALETTE
        if config['full_screen']:
            mode |= FULLSCREEN
            self.screen_real = pg.display.set_mode((640, 480), mode, 8)
        else:
            mode |= RESIZABLE
            self.screen_real = pg.display.set_mode(self.SCREEN_SIZE, mode, 8)
        icon = BytesIO(base64.decodestring(ICON))
        pg.display.set_icon(pg.image.load(icon).convert_alpha())
        mode = (RESIZABLE & mode) | (FULLSCREEN & mode)
        self.screen = pg.Surface((320, 200), mode, 8)
        self.screen_bak = pg.Surface((320, 200), mode, 8)

    @property
    def SCREEN_SIZE(self):
        return config['window_width'], config['window_height']

    @SCREEN_SIZE.setter
    def SCREEN_SIZE(self, val):
        config['window_width'], config['window_height'] = val

    @staticmethod
    def create_compatible_sized_surface(source, size):
        dest = pg.Surface(
            size or source.get_size(),
            source.get_flags(),
            source.get_bitsize(),
            source.get_masks()
        )
        dest.set_palette(source.get_palette())
        return dest

    create_compatible_surface = partialmethod(create_compatible_sized_surface, size=None)

    def switch_screen(self, speed):
        index = [0, 3, 1, 5, 2, 4]
        speed = (speed + 1) * 10
        for i in range(6):
            self.screen.lock()
            self.screen_bak.lock()
            y = 0
            x = index[i]
            buf_screen = pg.PixelArray(self.screen)
            buf_bak = pg.PixelArray(self.screen_bak)
            while y < 200:
                buf_bak[x, y] = buf_screen[x, y]
                x += 6
                if x >= 320:
                    x -= 320
                    y += 1
            del buf_bak
            del buf_screen
            self.screen_bak.unlock()
            self.screen.unlock()
            size = self.screen_real.get_size()
            self.screen_real.blit(
                pg.transform.scale(self.screen_bak, size), (0, 0)
            )
            pg.display.flip()
            self.delay(speed)

    def update_screen(self, rect=None):
        real_rect = self.screen_real.get_rect()
        size = real_rect.size
        if rect is not None:
            dst_rect = pg.Rect(
                math.floor(rect.x / 320.0 * pal_x(size)),
                math.floor(rect.y / 200.0 * pal_y(size)),
                math.ceil(rect.w / 320.0 * pal_x(size)),
                math.ceil(rect.h / 200.0 * pal_y(size)),
            )
            dst_rect = real_rect.clip(dst_rect)
            self.screen_real.blit(
                pg.transform.scale(
                    self.screen, size
                ).subsurface(dst_rect),
                dst_rect
            )
        elif self.shake_time != 0:
            w_zoom = pal_x(size) / 320.0
            h_zoom = pal_y(size) / 200.0
            src_rect = pg.Rect(0, 0, 320, 200 - self.shake_level)
            dst_rect = pg.Rect(
                (0, 0),
                (
                    320 * w_zoom,
                    (200 - self.shake_level) * h_zoom
                )
            )
            if self.shake_time & 1:
                src_rect.y = self.shake_level
            else:
                dst_rect.y = self.shake_level * h_zoom
            self.screen_real.blit(
                pg.transform.scale(
                    self.screen.subsurface(src_rect),
                    dst_rect.size
                ),
                dst_rect
            )
            if self.shake_time & 1:
                dst_rect.y = (pal_y(size) - self.shake_level) * h_zoom
            else:
                dst_rect.y = 0
            dst_rect.h = self.shake_level * h_zoom
            dst_rect = self.screen_real.get_rect().clip(dst_rect)
            self.screen_real.fill((0, 0, 0), dst_rect)
            self.shake_time -= 1
        else:
            self.screen_real.blit(pg.transform.scale(self.screen, size), (0, 0))
        if rect is None:
            pg.display.flip()
        else:
            pg.display.update(dst_rect)
        if self.screen_real.mustlock():
            self.screen_real.unlock()

    def blit(self, *args, **kwargs):
        self.screen.blit(*args, **kwargs)

    def fade_screen(self, speed):
        index = [0, 3, 1, 5, 2, 4]

        ticks = pg.time.get_ticks()
        speed = (speed + 1) * 10
        for i in range(12):
            for j in range(6):
                self.process_event()
                while pg.time.get_ticks() <= ticks:
                    self.process_event()
                    pg.time.delay(5)
                ticks = pg.time.get_ticks() + speed
                self.screen.lock()
                self.screen_bak.lock()
                y = 0
                x = index[j]
                buf_screen = pg.PixelArray(self.screen)
                buf_bak = pg.PixelArray(self.screen_bak)
                while y < 200:
                    a = buf_screen[x, y]
                    b = buf_bak[x, y]
                    if i > 0:
                        if (a & 0x0F) > (b & 0x0F):
                            b += 1
                        elif (a & 0x0F) < (b & 0x0F):
                            b -= 1
                    buf_bak[x, y] = (a & 0xF0) | (b & 0x0F)
                    x += 6
                    if x >= 320:
                        x -= 320
                        y += 1
                del buf_bak
                del buf_screen
                self.screen_bak.unlock()
                self.screen.unlock()
                size = self.screen_real.get_size()
                if self.shake_time != 0:
                    w_zoom = pal_x(size) / 320.0
                    h_zoom = pal_y(size) / 200.0
                    src_rect = pg.Rect(0, 0, 320, 200 - self.shake_level)
                    dst_rect = pg.Rect(
                        (0, 0),
                        (
                            320 * w_zoom,
                            (200 - self.shake_level) * h_zoom
                        )
                    )
                    if self.shake_time & 1:
                        src_rect.y = self.shake_level
                    else:
                        dst_rect.y = self.shake_level * h_zoom
                    self.screen_real.blit(
                        pg.transform.scale(
                            self.screen.subsurface(src_rect), dst_rect.size
                        ),
                        dst_rect
                    )
                    if self.shake_time & 1:
                        dst_rect.y = (pal_y(size) - self.shake_level) * h_zoom
                    else:
                        dst_rect.y = 0
                    dst_rect.h = self.shake_level * h_zoom
                    dst_rect = self.screen_real.get_rect().clip(dst_rect)
                    self.screen_real.fill((0, 0, 0), dst_rect)
                    self.shake_time -= 1
                else:
                    self.screen_real.blit(
                        pg.transform.scale(self.screen_bak, size), (0, 0)
                    )
                    pg.display.flip()
        self.screen.unlock()
        self.screen_bak.unlock()
        self.update_screen()
