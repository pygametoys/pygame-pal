#! /usr/bin/env python
# -*- coding: utf8 -*-
import base64
import copy
from io import BytesIO
import math
import re
import struct
import sys

import chardet
from configobj import ConfigObj
import wcwidth
from pygame import freetype

from pgpal.compat import pg, range, partialmethod, open_ignore_case as open
from pgpal.const import *
from pgpal.mkfext import Data, SSS, SubPlace
from pgpal.utils import Object, pal_x, pal_y
from pgpal import config


encoding = None
iso_font = bytearray(
    base64.b64decode(
b'''\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAYGBgYGBgYABgYAAAAAABs\nbDYAAAAAAAAAAAAAAAAANjZ/NjZ/NjY
AAAAAAAgIPmsLCz5oaGs+CAgAAAAAMxMYCAwEBjIzAAAA\nAAAcNjYcbD4zM3vOAAAAAAAYGA
wAAAAAAAAAAAAAAAAwGBgMDAwMDBgYMAAAAAAMGBgwMDAwMBgY\nDAAAAAAAAAA2HH8cNgAAA
AAAAAAAAAAYGH4YGAAAAAAAAAAAAAAAAAAAABgYDAAAAAAAAAAAAH4A\nAAAAAAAAAAAAAAAA
AAAAABgYAAAAAABgIDAQGAgMBAYCAwAAAAA+Y2Nja2tjY2M+AAAAAAAYHhgY\nGBgYGBgYAAA
AAAA+Y2BgMBgMBgN/AAAAAAA+Y2BgPGBgYGM+AAAAAAAwODw2M38wMDAwAAAAAAB/\nAwM/YG
BgYGM+AAAAAAA8BgMDP2NjY2M+AAAAAAB/YDAwGBgYDAwMAAAAAAA+Y2NjPmNjY2M+AAAA\nA
AA+Y2NjfmBgYDAeAAAAAAAAAAAYGAAAABgYAAAAAAAAAAAYGAAAABgYDAAAAABgMBgMBgYMG
DBg\nAAAAAAAAAAB+AAB+AAAAAAAAAAAGDBgwYGAwGAwGAAAAAAA+Y2AwMBgYABgYAAAAAAA8
ZnN7a2t7\nMwY8AAAAAAA+Y2Njf2NjY2NjAAAAAAA/Y2NjP2NjY2M/AAAAAAA8ZgMDAwMDA2Y
8AAAAAAAfM2Nj\nY2NjYzMfAAAAAAB/AwMDPwMDAwN/AAAAAAB/AwMDPwMDAwMDAAAAAAA8Zg
MDA3NjY2Z8AAAAAABj\nY2Njf2NjY2NjAAAAAAA8GBgYGBgYGBg8AAAAAAAwMDAwMDAwMDMeA
AAAAABjMxsPBwcPGzNjAAAA\nAAADAwMDAwMDAwN/AAAAAABjY3d/f2trY2NjAAAAAABjY2dv
b3t7c2NjAAAAAAA+Y2NjY2NjY2M+\nAAAAAAA/Y2NjYz8DAwMDAAAAAAA+Y2NjY2Njb3s+MGA
AAAA/Y2NjYz8bM2NjAAAAAAA+YwMDDjhg\nYGM+AAAAAAB+GBgYGBgYGBgYAAAAAABjY2NjY2
NjY2M+AAAAAABjY2NjYzY2HBwIAAAAAABjY2tr\na2t/NjY2AAAAAABjYzY2HBw2NmNjAAAAA
ADDw2ZmPDwYGBgYAAAAAAB/MDAYGAwMBgZ/AAAAAAA8\nDAwMDAwMDAw8AAAAAAADAgYEDAgY
EDAgYAAAAAA8MDAwMDAwMDA8AAAAAAgcNmMAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAP8AAAA
MDBgAAAAAAAAAAAAAAAAAAAA+YH5jY3NuAAAAAAADAwM7Z2NjY2c7\nAAAAAAAAAAA+YwMDA2
M+AAAAAABgYGBuc2NjY3NuAAAAAAAAAAA+Y2N/A2M+AAAAAAA8ZgYfBgYG\nBgYGAAAAAAAAA
ABuc2NjY3NuYGM+AAADAwM7Z2NjY2NjAAAAAAAMDAAMDAwMDAw4AAAAAAAwMAAw\nMDAwMDAw
MDMeAAADAwNjMxsPHzNjAAAAAAAMDAwMDAwMDAw4AAAAAAAAAAA1a2tra2trAAAAAAAA\nAAA
7Z2NjY2NjAAAAAAAAAAA+Y2NjY2M+AAAAAAAAAAA7Z2NjY2c7AwMDAAAAAABuc2NjY3NuYOB
g\nAAAAAAA7ZwMDAwMDAAAAAAAAAAA+Yw44YGM+AAAAAAAADAw+DAwMDAw4AAAAAAAAAABjY2
NjY3Nu\nAAAAAAAAAABjYzY2HBwIAAAAAAAAAABja2trPjY2AAAAAAAAAABjNhwcHDZjAAAAA
AAAAABjYzY2\nHBwMDAYDAAAAAAB/YDAYDAZ/AAAAAABwGBgYGA4YGBgYcAAAABgYGBgYGBgY
GBgYGAAAAAAOGBgY\nGHAYGBgYDgAAAAAAAAAAbjsAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'''
    )
)

if config['use_embedded_font']:
    with open('wor16.fon', 'rb') as f:
        pos = 0x682
        f.seek(pos)
        font_data = bytearray(f.read())

if not (config['use_embedded_font'] and config['use_iso_font']):
    freetype.init()
    unicode_font = freetype.Font(config['font_file'], 16)


def get_char_width(o):
    width = wcwidth.wcwidth(o)
    return width << 3


class Desc(Object):
    DESC_RE = re.compile('(.*)\((.*)\)=(.*)')

    def __init__(self):
        with open('desc.dat', 'rb') as f:
            self.descs = {}
            content = f.read().decode(encoding, errors="replace")
            for index, name, desc in self.DESC_RE.findall(content):
                self.descs[int(index, 16)] = desc.strip()

    def __getitem__(self, index):
        return self.descs.get(index, None)


class Word(Object):
    def __init__(self, word_length):
        self.word_length = word_length
        with open('word.dat', 'rb') as f:
            self.data = f.read()
        global encoding
        if encoding is None:
            encoding = chardet.detect(self.data)['encoding']
            if encoding.lower() in {'gb2312', 'iso-8859-1'}:
                encoding = 'gbk'
        self.init_fonts()

    def init_fonts(self):
        if config['use_embedded_font']:
            global char_data
            with open('wor16.asc', 'rb') as f:
                content = f.read()
                char_data = content.decode(encoding, 'replace')

    def __getitem__(self, index):
        return self.data[
            index * self.word_length:
            (index + 1) * self.word_length
        ].rstrip(b'\x20\x00').decode(encoding, 'replace')


class Msg(Object):
    def __init__(self):
        self.indexes = SSS().read(3)
        msg_file = 'm.msg'
        with open(msg_file, 'rb') as f:
            self.msg = f.read()

    def __getitem__(self, msgid):
        begin, end = struct.unpack_from('2I', self.indexes, msgid * 4)
        return self.msg[begin: end].decode(encoding, 'replace')


class TextPrinterMixin(object):
    def __init__(self):
        self.word_length = 10
        if config['msg_file']:
            with open(config['msg_file'], 'rb') as f:
                content = f.read()
                cfg_content, msg_content = content.split(b'\n[BEGIN MESSAGE]', 1)
                msg_content = b'[BEGIN MESSAGE]' + msg_content
                cfg = ConfigObj(BytesIO(cfg_content), encoding='utf-8')
                if cfg['BEGIN SETTING']['UseISOFont']:
                    config['use_iso_font'] = True
                self.words = {int(i): word for i, word in cfg['BEGIN WORDS'].items()}
                self.msgs = []
                self.msg_index = {}
                for sid, block, eid in re.findall(u'\[BEGIN MESSAGE\] (\d+)([\s\S]+?)\[END MESSAGE\] (\d+)', msg_content.decode('utf-8'), re.UNICODE):
                    item = int(sid)
                    self.msg_index[item] = []
                    for line in block.strip().splitlines():
                        if line != '[CLEAR MESSAGE]':
                            self.msg_index[item].append(len(self.msgs))
                            self.msgs.append(line)
                        else:
                            self.msg_index[item].append(0)
                offset = 1
                for slot in self.screen_layout.__slots__:
                    attr = getattr(self.screen_layout, slot)
                    if isinstance(attr, list):
                        for i in range(len(attr)):
                            attr[i] = tuple(int(x) for x in cfg['BEGIN LAYOUT'][str(offset)])
                            offset += 1
                    elif isinstance(attr, tuple):
                        item = tuple(int(x) for x in cfg['BEGIN LAYOUT'][str(offset)])
                        setattr(self.screen_layout, slot, item)
                        offset += 1
                    if offset == 75:
                        offset = 81
                self.use_custom_screen_layout = True
        else:
            self.words = Word(self.word_length)
            self.msgs = Msg()
            self.use_custom_screen_layout = False
        self.delay_time = 3
        self.updated_in_battle = False
        self.current_dialog_line_num = 0
        self.dialog_icons = SubPlace(Data().read(12))
        self.current_font_color = FONT_COLOR_DEFAULT
        self.icon = 0
        self.pos_icon = 0
        self.pos_dialog_title = 12, 8
        self.pos_dialog_text = 44, 26
        self.dialog_position = DialogPos.Upper
        self.dialog_shadow = 0
        self.user_skip = False
        try:
            self.descs = Desc()
        except Exception:
            self.descs = None
        self.no_desc = False

    @staticmethod
    def text_width(item_text):
        return sum(get_char_width(char) for char in item_text)

    def word_width(self, word_index):
        item_text = self.words[word_index]
        w = self.text_width(item_text)
        return (w + 8) >> 4

    def word_max_width(self, first_index, words_num):
        return max(
            self.word_width(index)
            for index in range(first_index, first_index + words_num)
        )

    def menu_text_max_width(self, menu_items):
        return max(
            (self.text_width(menu_item.label) + 8) >> 4
            for menu_item in menu_items
        )

    def draw_number(self, num, length, pos, color, align):
        if color == NumColor.Blue:
            f = 29
        elif color == NumColor.Cyan:
            f = 56
        else:
            f = 19
        i = num
        actual_length = 0
        while i > 0:
            i //= 10
            actual_length += 1
        actual_length = min(length, actual_length) or 1
        x, y = pos
        x -= 6
        if align == NumAlign.Left:
            x += 6 * actual_length
        elif align == NumAlign.Mid:
            x += 3 * (length + actual_length)
        elif align == NumAlign.Right:
            x += 6 * length
        for _ in range(actual_length):
            self.sprite_ui[f + num % 10].blit_to(self.screen, (x, y))
            x -= 6
            num //= 10

    def draw_text(self, text, pos, color, shadow, update):
        if len(pos) > 2:
            use_8x8_font = pos[2]
            pos = pos[:2]
        else:
            use_8x8_font = False
        x, y = pos
        urect = pg.Rect(pos, (0, 16 + shadow))
        if x > 320:
            return
        for char in text:
            if shadow:
                self.draw_char_on_surface(
                    char, (x + 1, y + 1), 0, use_8x8_font
                )
                self.draw_char_on_surface(
                    char, (x + 1, y), 0, use_8x8_font
                )
            self.draw_char_on_surface(char, (x, y), color, use_8x8_font)
            char_width = get_char_width(char)
            x += char_width
            urect.w += char_width
        if update and urect.w > 0:
            if shadow:
                urect.w += 1
            if urect.x + urect.w > 320:
                urect.w = 320 - urect.x
            self.update_screen(urect)

    def start_dialog_with_offset(
        self,
        dialog_location,
        font_color,
        num_char_face,
        playing_rng,
        x_off,
        y_off
    ):
        if self.in_battle and self.updated_in_battle:
            self.update_screen()
            self.updated_in_battle = True
        self.icon = 0
        self.pos_icon = 0
        self.current_dialog_line_num = 0
        self.pos_dialog_title = 12, 8
        self.user_skip = False
        if font_color != 0:
            self.current_font_color = font_color
        if playing_rng and num_char_face:
            self.screen_bak.blit(self.screen, (0, 0))
            self.playing_rng = True
        if dialog_location == DialogPos.Upper:
            if num_char_face > 0:
                w, h = self.rgm[num_char_face].size
                pos = (
                    max(48 - w // 2 + x_off, 0),
                    max(55 - h // 2 + y_off, 0)
                )
                self.rgm[num_char_face].blit_to(self.screen, pos)
                rect = pg.Rect(pos, (w, h))
                self.update_screen(rect)
                self.pos_dialog_title = 80, 8
                self.pos_dialog_text = 96, 26
            else:
                self.pos_dialog_title = 12, 8
                self.pos_dialog_text = 44, 26
        elif dialog_location == DialogPos.Center:
            self.pos_dialog_text = 80, 40
        elif dialog_location == DialogPos.Lower:
            if num_char_face > 0:
                pos = (
                    270 - self.rgm[num_char_face].width // 2 + x_off,
                    144 - self.rgm[num_char_face].height // 2 + y_off,
                )
                self.rgm[num_char_face].blit_to(self.screen, pos)
                self.update_screen()
                self.pos_dialog_title = 4, 108
                self.pos_dialog_text = 20, 126
            else:
                self.pos_dialog_title = 12, 108
                self.pos_dialog_text = 44, 126
        elif dialog_location == DialogPos.CenterWindow:
            self.pos_dialog_text = 160, 40
        self.pos_dialog_title = (
            pal_x(self.pos_dialog_title) + x_off,
            pal_y(self.pos_dialog_title) + y_off
        )
        self.pos_dialog_text = (
            pal_x(self.pos_dialog_text) + x_off,
            pal_y(self.pos_dialog_text) + y_off
        )
        self.dialog_position = dialog_location

    start_dialog = partialmethod(start_dialog_with_offset, x_off=0, y_off=0)

    def clear_dialog(self, wait_for_key):
        if self.current_dialog_line_num > 0 and wait_for_key:
            self.dialog_wait_for_key()
        self.current_dialog_line_num = 0
        if self.dialog_position == DialogPos.Center:
            self.pos_dialog_title = 12, 8
            self.pos_dialog_text = 44, 26
            self.current_font_color = FONT_COLOR_DEFAULT
            self.dialog_position = DialogPos.Upper

    def end_dialog(self):
        self.clear_dialog(True)
        self.pos_dialog_text = 12, 8
        self.pos_dialog_text = 44, 26
        self.current_font_color = FONT_COLOR_DEFAULT
        self.dialog_position = DialogPos.Upper
        self.user_skip = False
        self.playing_rng = False

    @property
    def is_in_dialog(self):
        return bool(self.current_dialog_line_num)

    def show_dialog_text(self, text):
        self.clear_key_state()
        self.icon = 0
        if self.in_battle and not self.updated_in_battle:
            self.update_screen()
            self.updated_in_battle = False
        if self.current_dialog_line_num > 3:
            self.dialog_wait_for_key()
            self.current_dialog_line_num = 0
            self.blit(self.screen_bak, (0, 0))
            self.update_screen()
        x = pal_x(self.pos_dialog_text)
        y = pal_y(self.pos_dialog_text) + self.current_dialog_line_num * 18
        if self.dialog_position == DialogPos.CenterWindow:
            length = wcwidth.wcswidth(text)
            pos = (
                pal_x(self.pos_dialog_text) - length * 4,
                pal_y(self.pos_dialog_text)
            )
            box = self.one_line_box_with_shadow(
                pos, (length + 1) // 2,
                False, self.dialog_shadow
            )
            rect = pg.Rect(
                pos, (320 - pal_x(pos) * 2 + 32, 64)
            )
            self.update_screen(rect)
            self.display_text(
                text,
                pal_x(pos) + 8 + ((length & 1) << 2),
                pal_y(pos) + 10, True
            )
            self.update_screen(rect)
            self.dialog_wait_for_key_with_maximum_seconds(1.4)
            self.delete_box(box)
            self.update_screen(rect)
            self.end_dialog()
        else:
            if (
                self.current_dialog_line_num == 0 and
                self.dialog_position != DialogPos.Center and
                text[-1] in {u'\uff1a', u'\u2236', u':'}
            ):
                self.draw_text(
                    text, self.pos_dialog_title,
                    FONT_COLOR_CYAN_ALT, True, True
                )
            else:
                if not self.playing_rng and self.current_dialog_line_num == 0:
                    self.screen_bak.blit(self.screen, (0, 0))
                x = self.display_text(text, x, y, False)
                if self.user_skip:
                    self.update_screen()
                self.pos_icon = x, y
                self.current_dialog_line_num += 1

    def display_text(self, text, x, y, is_dialog):
        i = 0
        is_number = False
        while i < len(text):
            char = text[i]
            if char == '-':
                if self.current_font_color == FONT_COLOR_CYAN:
                    self.current_font_color = FONT_COLOR_DEFAULT
                else:
                    self.current_font_color = FONT_COLOR_CYAN
                i += 1
            elif char == "'" and False:
                if self.current_font_color == FONT_COLOR_RED:
                    self.current_font_color = FONT_COLOR_DEFAULT
                else:
                    self.current_font_color = FONT_COLOR_RED
                i += 1
            elif char == '@':
                if self.current_font_color == FONT_COLOR_RED_ALT:
                    self.current_font_color = FONT_COLOR_DEFAULT
                else:
                    self.current_font_color = FONT_COLOR_RED_ALT
                i += 1
            elif char == '"':
                if self.current_font_color == FONT_COLOR_YELLOW:
                    self.current_font_color = FONT_COLOR_DEFAULT
                else:
                    self.current_font_color = FONT_COLOR_YELLOW
                i += 1
            elif char == '$':
                num = re.compile('^\d+').match(text[i+1:]).group(0)
                self.delay_time = int(num) * 10 // 7
                i += 3
            elif char == '~':
                if self.user_skip:
                    self.update_screen()
                num = re.compile('^\d+').match(text[i+1:]).group(0)
                if not is_dialog:
                    self.delay(int(num) * 80 // 7)
                self.current_dialog_line_num = -1
                self.user_skip = False
                return x
            elif char == ')':
                self.icon = 1
                i += 1
            elif char == '(':
                self.icon = 2
                i += 1
            elif char == '\\':
                i += 1
            else:
                color = self.current_font_color
                if is_dialog:
                    if self.current_font_color == FONT_COLOR_DEFAULT:
                        color = 0
                    is_number = char.isdigit()
                if is_number:
                    self.draw_number(
                        int(char), 1, (x, y + 4),
                        NumColor.Yellow, NumAlign.Left
                    )
                else:
                    self.draw_text(
                        char, (x, y), color,
                        not is_dialog,
                        not (is_dialog or self.user_skip)
                    )
                x += get_char_width(char)
                if not (is_dialog or self.user_skip):
                    self.clear_key_state()
                    self.delay(self.delay_time * 8)
                    if self.input_state.key_press & (Key.Search | Key.Menu):
                        self.user_skip = True
                i += 1
        return x

    def dialog_wait_for_key_with_maximum_seconds(self, max_seconds):
        beginning_ticks = pg.time.get_ticks()
        current_palette = self.get_palette()
        palette = copy.deepcopy(current_palette)
        if self.dialog_position not in {DialogPos.CenterWindow, DialogPos.Center}:
            p = self.dialog_icons[self.icon]
            if p is not None:
                rect = pg.Rect(self.pos_icon, (16, 16))
                p.blit_to(self.screen, self.pos_icon)
                self.update_screen(rect)
        self.clear_key_state()
        while True:
            self.delay(100)
            if self.dialog_position not in {DialogPos.CenterWindow, DialogPos.Center}:
                t = palette[0xF9]
                palette[0xF9:0xFE] = palette[0xF9+1:0xFE+1]
                palette[0xFE] = t
                self.set_screen_palette(palette)
            if (
                math.fabs(max_seconds) > sys.float_info.epsilon and
                pg.time.get_ticks() - beginning_ticks > 1000 * max_seconds
            ):
                break
            if self.input_state.key_press != 0:
                break
        if self.dialog_position not in {DialogPos.CenterWindow, DialogPos.Center}:
            self.set_palette(self.num_palette, self.night_palette)
        self.clear_key_state()
        self.user_skip = False

    dialog_wait_for_key = partialmethod(
        dialog_wait_for_key_with_maximum_seconds, 0
    )

    def show_cash(self, cash):
        box = self.one_line_box((0, 0), 5, True)
        self.draw_text(self.words[CASH_LABEL], (10, 10), 0, False, False)
        self.draw_number(cash, 6, (49, 14), NumColor.Yellow, NumAlign.Right)
        return box

    def draw_char_on_surface(self, char, pos, color, use_8x8_font, surface=None):
        if surface is None:
            surface = self.screen
        x, y = pos
        if ord(char) >= 0x80:
            if config['use_embedded_font']:
                if char in char_data:
                    index = char_data.index(char)
                    char_ptr = index * 30
                    for i in range(30):
                        dx = x + ((i & 1) << 3)
                        char_byte = font_data[char_ptr + i]
                        for j in range(8):
                            if char_byte & (1 << (7 - j)):
                                surface.set_at((dx, y), color)
                            dx += 1
                        y += i & 1
                return
        else:
            if config['use_iso_font'] and use_8x8_font:
                char_ptr = (ord(char) & 0x7f) * 15
                for i in range(15):
                    dx = x
                    char_byte = iso_font[char_ptr + i]
                    for j in range(8):
                        if char_byte & (1 << j):
                            surface.set_at((dx, y), color)
                        dx += 1
                    y += (i & 1)
                return
        surf, rect = unicode_font.render(char)
        if use_8x8_font:
            rect.y += rect.y % 2
            rect.y //= 2
            rect.h += rect.h % 2
            rect.h //= 2
            surf = pg.transform.scale(surf, rect.size)
        pxarray = pg.PixelArray(surf)
        x += rect.x
        if use_8x8_font:
            y += 5 - rect.y
        else:
            y += 12 - rect.y
        for i in range(rect.w):
            for j in range(rect.h):
                has_color = pxarray[i, j]
                if has_color:
                    surface.set_at((x + i + 1, y + j + 1), color)
