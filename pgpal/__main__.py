#! /usr/bin/env python
# -*- coding: utf8 -*-
import struct
from random import randrange
from pgpal.game import *

class Crane(pg.sprite.DirtySprite):

    def __init__(self, x, y, frame, sprite):
        pg.sprite.DirtySprite.__init__(self)
        self.SpriteCrane = sprite
        self.frame = frame
        self.rect = pg.Rect(
            (x, y),
            (0, 0)
        )

    def update(self, img_pos, surface):
        self.frame = (self.frame + (self.groups()[0].crane_frame & 1)) % 8
        self.rect.size = self.SpriteCrane[self.frame].size
        self.SpriteCrane[self.frame].blit_to(surface, self.rect)
        self.rect.y += img_pos > 1 and img_pos & 1
        self.rect.x -= 1
        if self.rect.x + self.rect.w < 0:
            self.kill()


def run():
    try:
        game = ChinesePaladin()
        trademark_screen(game)
        splash_screen(game)
        main_game(game)
    except SystemExit:
        pass
    except:
        error_box(traceback.format_exc(limit=1))

def trademark_screen(game):
    if game.play_video('1.AVI'):
        return
    game.set_palette(3)
    game.play_rng(6, 0, 1000, 25)
    game.delay(1000)
    game.fadeout(1)


def splash_screen(game):
    if game.play_video('2.AVI'):
        return
    palette = game.get_palette(1, False)
    bitmap_down = pg.Surface((320, 200), depth=8)
    game.fbp.render(BITMAPNUM_SPLASH_DOWN, bitmap_down)
    bitmap_up = pg.Surface((320, 200), depth=8)
    game.fbp.render(BITMAPNUM_SPLASH_UP, bitmap_up)
    bitmap_title = game.mgo[SPRITENUM_SPLASH_TITLE][0]
    cranes = pg.sprite.Group(
        Crane(
            randrange(300, 600),
            randrange(0, 80),
            randrange(0, 8),
            game.mgo[SPRITENUM_SPLASH_CRANE]
        ) for _ in range(9)
    )
    cranes.crane_frame = 0
    if not game.play_cd_track(7):
        game.play_music(NUM_RIX_TITLE, True, 2)
    img_pos = 200
    game.process_event()
    game.clear_key_state()
    begin_time = pg.time.get_ticks()
    src_rect = pg.Rect((0, 0), (320, 0))
    dst_rect = pg.Rect((0, 0), (320, 0))
    title_rect = pg.Rect(
        (255, 10),
        (bitmap_title.width, 0)
    )
    while True:
        game.process_event()
        curtime = pg.time.get_ticks() - begin_time
        if curtime < 15000:
            current_palette = [
                pg.Color(
                    int(color.r * (curtime / 15000.0)),
                    int(color.g * (curtime / 15000.0)),
                    int(color.b * (curtime / 15000.0)),
                ) for color in palette
            ]
        game.set_screen_palette(current_palette)
        bitmap_down.set_palette(current_palette)
        bitmap_up.set_palette(current_palette)
        if img_pos > 1:
            img_pos -= 1
        src_rect.top = img_pos
        dst_rect.height = src_rect.height = 200 - img_pos
        dst_rect.top = 0
        game.blit(bitmap_up, dst_rect, src_rect)
        src_rect.top = 0
        dst_rect.height = src_rect.height = img_pos
        dst_rect.top = 200 - img_pos
        game.blit(bitmap_down, dst_rect, src_rect)
        cranes.update(img_pos, game.screen)
        cranes.crane_frame += 1
        title_rect.h = min(title_rect.h + 1, bitmap_title.height)
        bitmap_title.blit_to(game.screen, title_rect)
        game.update_screen()
        if game.input_state.key_press & (Key.Menu | Key.Search):
            bitmap_title.blit_to(game.screen, title_rect.topleft)
            game.update_screen()
            if curtime < 15000:
                while curtime < 15000:
                    current_palette = [
                        pg.Color(
                            int(color.r * (curtime / 15000.0)),
                            int(color.g * (curtime / 15000.0)),
                            int(color.b * (curtime / 15000.0)),
                        ) for color in palette
                    ]
                    game.set_screen_palette(current_palette)
                    game.delay(8)
                    curtime += 250
                game.delay(500)
            break
        game.process_event()
        while pg.time.get_ticks() - begin_time < curtime + 85:
            pg.time.delay(1)
            game.process_event()
    if config['cd'] is None:
        game.play_music(0, False, 1)
    game.fadeout(1)
    cranes.empty()


def main_game(game):
    game.cur_save_slot = game.opening_menu()
    game.init_game_data(game.cur_save_slot)
    ticks = pg.time.get_ticks()
    while True:
        if game.to_start:
            game.start()
            game.to_start = False
        game.load_resources()
        game.clear_key_state()
        game.delay_until(ticks)
        ticks = pg.time.get_ticks() + FRAME_TIME
        game.start_frame()


def main():
    if sys.version_info[0] == 2 and struct.calcsize('P') == 4:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass
    pg.init()
    run()


if __name__ == '__main__':
    main()
