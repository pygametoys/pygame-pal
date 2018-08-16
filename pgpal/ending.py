#! /usr/bin/env python
# -*- coding: utf8 -*-
from functools import partial
from pgpal.compat import pg, range
from pgpal.mkfbase import is_win95


class EndingTheaterMixin(object):
    def __init__(self):
        self.cur_effect_sprite = 0

    def ending_animation(self):
        y_pos_girl = 180
        upper = self.create_compatible_surface(self.screen)
        self.fbp.render(
            69 if is_win95 else 61, upper
        )
        lower = self.create_compatible_surface(self.screen)
        self.fbp.render(
            70 if is_win95 else 62, lower
        )
        buf = self.mgo[571]
        buf_girl = self.mgo[572]
        src_rect = pg.Rect(0, 0, 320, 0)
        dst_rect = pg.Rect(0, 0, 320, 0)
        self.screen_wave = 2
        for i in range(400):
            src_rect.h = dst_rect.h = 200 - i // 2
            src_rect.y, dst_rect.y = 0, i // 2
            self.blit(lower, dst_rect, src_rect)
            src_rect.h = dst_rect.h = i // 2
            src_rect.y, dst_rect.y = 200 - i // 2, 0
            self.blit(upper, dst_rect, src_rect)
            self.apply_wave(self.screen)
            buf[0].blit_to(self.screen, (0, -400 + i))
            buf[1].blit_to(self.screen, (0, -200 + i))
            y_pos_girl -= i & 1
            if y_pos_girl < 80:
                y_pos_girl = 80
            buf_girl[(pg.time.get_ticks() // 50) % 4].blit_to(
                self.screen, (220, y_pos_girl)
            )
            self.update_screen()
            if self.need_fadein:
                self.fadein(1)
                self.need_fadein = False
                upper.set_palette(self.screen.get_palette())
                lower.set_palette(self.screen.get_palette())
            self.delay(50)
        self.screen_wave = 0

    def ending_screen(self):
        self.play_video('4.AVI')
        avi_played = self.play_video('5.AVI')
        if not avi_played:
            win_music = self.play_cd_track(12)
            if not win_music:
                self.play_music(0x1a, True, 0)
            self.play_rng(self.cur_playing_rng, 110, 150, 7)
            self.play_rng(self.cur_playing_rng, 151, 999, 9)
            self.fadeout(2)
            if not win_music:
                self.play_music(0x19, True, 0)
            self.show_fbp(75, 0)
            self.fadein(1, 5, False)
            self.scroll_fbp(74, 0xf, True)
            self.fadeout(1)
            self.screen.fill((0, 0, 0))
            self.num_palette = 4
            self.need_fadein = True
            self.ending_animation()
            if not win_music:
                self.play_music(0, False, 2)
            if not win_music and not self.play_cd_track(2):
                self.play_music(0x11, True, 0)
            self.screen.fill((0, 0, 0))
            self.set_palette(0, False)
            self.play_rng(0xb, 0, 999, 7)
            self.fadeout(2)
            self.screen.fill((0, 0, 0))
            self.num_palette = 8
            self.need_fadein = True
            self.play_rng(10, 0, 999, 6)
            self.cur_effect_sprite = 0
            self.show_fbp(77, 10)
            self.screen_bak.blit(self.screen, (0, 0))
            self.cur_effect_sprite = 0x27b
            self.show_fbp(76, 7)
            self.set_palette(5, False)
            self.show_fbp(73, 7)
            self.scroll_fbp(72, 0xf, True)
            self.show_fbp(71, 7)
            self.show_fbp(68, 7)
            self.cur_effect_sprite = 0
            self.show_fbp(68, 6)
            self.wait_for_key(0)
            self.play_music(0, False, 1)
            self.delay(500)
        if not self.play_video('6.AVI'):
            if avi_played:
                self.need_fadein = False
                self.set_palette(5, False)
                self.cur_effect_sprite = 0
            if not self.play_cd_track(13):
                self.play_music(9, True, 0)
            self.scroll_fbp(67, 0xf, True)
            self.scroll_fbp(66, 0xf, True)
            self.scroll_fbp(65, 0xf, True)
            self.scroll_fbp(64, 0xf, True)
            self.scroll_fbp(63, 0xf, True)
            self.scroll_fbp(62, 0xf, True)
            self.scroll_fbp(61, 0xf, True)
            self.scroll_fbp(60, 0xf, True)
            self.scroll_fbp(59, 0xf, True)
            self.play_music(0, False, 6)
            self.fadeout(3)

    def scroll_fbp(self, chunk_num, scroll_speed, scroll_down):
        p = self.create_compatible_surface(self.screen)
        p.blit(self.screen, (0, 0))
        self.screen_bak.blit(self.screen, (0, 0))
        self.fbp.render(chunk_num, p)
        if scroll_speed == 0:
            scroll_speed = 1
        rect = pg.Rect(0, 0, 320, 0)
        dst_rect = pg.Rect(0, 0, 320, 0)
        for l in range(220):
            i = min(l, 200)
            rect.h = dst_rect.h = 200 - i
            if scroll_down:
                rect.y, dst_rect.y = 0, i
            else:
                rect.y, dst_rect.y = i, 0
            self.blit(self.screen_bak, dst_rect, rect)
            rect.h = dst_rect.h = i
            if scroll_down:
                rect.y, dst_rect.y = 200 - i, 0
            else:
                rect.y, dst_rect.y = 0, 200 - i
            self.blit(p, dst_rect, rect)
            self.apply_wave(self.screen)
            if self.cur_effect_sprite != 0:
                f = pg.time.get_ticks() // 50
                buf_sprite = self.mgo[self.cur_effect_sprite]
                buf_sprite[f % len(buf_sprite)].blit_to(self.screen, (0, 0))
            self.update_screen()
            if self.need_fadein:
                self.fadein(1)
                self.need_fadein = False
                p.set_palette(self.screen.get_palette())
            self.delay(800 // scroll_speed)
        self.blit(p, (0, 0))
        del p
        self.update_screen()

    def show_fbp(self, chunk_num, fade):
        index = [0, 3, 1, 5, 2, 4]
        if self.cur_effect_sprite != 0:
            buf_sprite = self.mgo[self.cur_effect_sprite]
        buf = partial(self.fbp.render, chunk_num)
        if fade:
            p = self.create_compatible_surface(self.screen)
            fade = (fade + 1) * 10
            buf(p)
            self.screen_bak.blit(self.screen, (0, 0))
            for i in range(16):
                for j in range(6):
                    self.screen_bak.lock()
                    y = 0
                    x = index[j]
                    buf_screen = pg.PixelArray(p)
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
                    self.blit(self.screen_bak, (0, 0))
                    if self.cur_effect_sprite != 0:
                        f = pg.time.get_ticks() // 150
                        buf_sprite[f % len(buf_sprite)].blit_to(self.screen, (0, 0))
                    self.update_screen()
                    self.delay(fade)
            del p
        if chunk_num != (68 if is_win95 else 49):
            buf(self.screen)
        self.update_screen()
