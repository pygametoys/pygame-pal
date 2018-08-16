# -*- coding: UTF-8 -*-
import attr
import datetime
from pgpal.const import *
from pgpal.compat import pg
from pgpal import config

if config['enable_joystick']:
    pg.joystick.init()


@attr.s
class InputState(object):
    curdir = attr.ib(converter=Direction, default=4)
    prevdir = attr.ib(converter=Direction, default=4)
    key_press = attr.ib(factory=int)
    if config['enable_joystick']:
        axis_x = attr.ib(factory=int)
        axis_y = attr.ib(factory=int)
        joystick_need_update = attr.ib(factory=bool)


class ControllerMixin(object):
    def __init__(self):
        self.input_state = InputState()
        self.key_last_time = {key: 0 for key in keymap}
        if not config['enable_mouse']:
            pg.mouse.set_visible(False)

    def clear_key_state(self):
        self.input_state.key_press = 0

    def wait_for_key(self, timeout):
        time_out = pg.time.get_ticks() + timeout
        self.clear_key_state()
        while timeout == 0 or pg.time.get_ticks() < time_out:
            self.delay(5)
            if self.input_state.key_press & (Key.Search | Key.Menu):
                break

    def process_event(self):
        if config['enable_joystick']:
            self.input_state.joystick_need_update = False
        events = pg.event.get()
        for event in events:
            if event.type == QUIT:
                self.shutdown(0)
            elif event.type == VIDEORESIZE:
                if not config['full_screen']:
                    self.SCREEN_SIZE = event.size
                    mode = self.screen.get_flags()
                    depth = self.screen.get_bitsize()
                    if depth == 8:
                        palette = self.screen.get_palette()
                        self.screen_real = pg.display.set_mode(self.SCREEN_SIZE, mode, depth)
                        self.set_screen_palette(palette)
                        self.update_screen()
            else:
                self.keyboard_event_filter(event)
                if config['enable_mouse']:
                    self.mouse_event_filter(event)
                if config['enable_joystick']:
                    self.joystick_event_filter(event)
        self.update_keyboard_state()
        if config['enable_joystick']:
            self.update_joystick_state()

    def keyboard_event_filter(self, event):
        if event.type == KEYDOWN:
            if event.mod & KMOD_ALT:
                if event.key == K_RETURN:
                    mode = self.screen.get_flags()
                    depth = self.screen.get_bitsize()
                    if depth == 8:
                        config['full_screen'] = not config['full_screen']
                        palette = self.screen.get_palette()
                        if config['full_screen']:
                            mode &= ~RESIZABLE
                            mode |= FULLSCREEN
                            self.screen_real = pg.display.set_mode((640, 480), mode, depth)
                        else:
                            mode &= ~FULLSCREEN
                            mode |= RESIZABLE
                            self.screen_real = pg.display.set_mode(
                                self.SCREEN_SIZE, mode, depth
                            )
                        self.set_screen_palette(palette)
                        self.update_screen()
                elif event.key == K_F4:
                    self.shutdown(0)
            elif event.key == K_p:
                pg.image.save(
                    self.screen_real,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S%f.bmp')
                )

    def mouse_event_filter(self, event):
        if event.type in {MOUSEBUTTONDOWN, MOUSEBUTTONUP}:
            screen_width, screen_height = self.screen_real.get_size()
            grid_width = screen_width // 3
            grid_height = screen_height // 3
            mx, my = event.pos
            thumbx = math.ceil(mx / grid_width)
            thumby = math.floor(my / grid_height)
            grid_index = thumbx + thumby * 3 - 1
            if event.type == MOUSEBUTTONDOWN:
                if event.button == KMOD_LSHIFT:
                    if grid_index == 2:
                        self.input_state.prevdir = self.input_state.curdir
                        self.input_state.curdir = Direction.North
                    elif grid_index == 6:
                        self.input_state.prevdir = self.input_state.curdir
                        self.input_state.curdir = Direction.South
                    elif grid_index == 0:
                        self.input_state.prevdir = self.input_state.curdir
                        self.input_state.curdir = Direction.West
                    elif grid_index == 8:
                        self.input_state.prevdir = self.input_state.curdir
                        self.input_state.curdir = Direction.East
                    elif grid_index == 1:
                        self.input_state.key_press |= Key.Up
                    elif grid_index == 7:
                        self.input_state.key_press |= Key.Down
                    elif grid_index == 3:
                        self.input_state.key_press |= Key.Left
                    elif grid_index == 5:
                        self.input_state.key_press |= Key.Right
            else:
                if event.button == KMOD_LSHIFT:
                    if grid_index in {0, 2, 6, 8}:
                        self.input_state.prevdir = Direction.Unknown
                        self.input_state.curdir = Direction.Unknown
                    elif grid_index == 4:
                        self.input_state.key_press |= Key.Search
                elif event.button == KMOD_SHIFT:
                    if grid_index == 4:
                        self.input_state.key_press |= Key.Menu
                    elif grid_index == 1:
                        self.input_state.key_press |= Key.Force
                    elif grid_index == 7:
                        self.input_state.key_press |= Key.Repeat
                    elif grid_index == 3:
                        self.input_state.key_press |= Key.Auto
                    elif grid_index == 5:
                        self.input_state.key_press |= Key.Defend

    def joystick_event_filter(self, event):
        if event.type == JOYAXISMOTION:
            self.input_state.joystick_need_update = True
            if event.axis == 0:
                if event.value > 3200:
                    self.input_state.axis_x = 1
                elif event.value < -3200:
                    self.input_state.axis_x = -1
                else:
                    self.input_state.axis_x = 0
            elif event.axis == 1:
                if event.value > 3200:
                    self.input_state.axis_y = 1
                elif event.value < -3200:
                    self.input_state.axis_y = -1
                else:
                    self.input_state.axis_y = 0
        elif event.type == JOYBUTTONDOWN:
            if event.button & 1 == 0:
                self.input_state.key_press |= Key.Menu
            elif event.button & 1 == 1:
                self.input_state.key_press |= Key.Search
        elif event.type == JOYHATMOTION:
            self.input_state.prevdir = Direction.Unknown if self.in_battle else self.input_state.curdir
            if event.value in {HAT_LEFT, HAT_LEFTUP}:
                self.input_state.curdir = Direction.West
                self.input_state.key_press |= Key.Left
            elif event.value in {HAT_RIGHT, HAT_RIGHTDOWN}:
                self.input_state.curdir = Direction.East
                self.input_state.key_press |= Key.Right
            elif event.value in {HAT_UP, HAT_RIGHTUP}:
                self.input_state.curdir = Direction.North
                self.input_state.key_press |= Key.Up
            elif event.value in {HAT_DOWN, HAT_LEFTDOWN}:
                self.input_state.curdir = Direction.South
                self.input_state.key_press |= Key.Down
            elif event.value == HAT_CENTERED:
                self.input_state.curdir = Direction.Unknown
                self.input_state.key_press |= Key.Null

    def update_keyboard_state(self):
        current_time = pg.time.get_ticks()
        key_state = pg.key.get_pressed()
        for key in keymap:
            if key_state[key]:
                if current_time > self.key_last_time[key]:
                    mapped = keymap[key]
                    if mapped in dir_map:
                        if self.input_state.curdir != dir_map[mapped]:
                            self.input_state.prevdir = Direction.Unknown if self.in_battle else self.input_state.curdir
                            self.input_state.curdir = dir_map[mapped]
                    self.input_state.key_press |= mapped
                    self.key_last_time[key] = 0xFFFFFFFF
            else:
                if self.key_last_time[key] != 0:
                    mapped = keymap[key]
                    if mapped in dir_map:
                        if self.input_state.curdir == dir_map[mapped]:
                            self.input_state.curdir = self.input_state.prevdir
                        self.input_state.prevdir = Direction.Unknown
                    self.key_last_time[key] = 0

    def update_joystick_state(self):
        if self.input_state.axis_x == 1 and self.input_state.axis_y >= 0:
            self.input_state.prevdir = self.input_state.curdir
            self.input_state.curdir = Direction.East
            self.input_state.key_press |= Key.Right
        elif self.input_state.axis_x == -1 and self.input_state.axis_y <= 0:
            self.input_state.prevdir = self.input_state.curdir
            self.input_state.curdir = Direction.West
            self.input_state.key_press |= Key.Left
        elif self.input_state.axis_x == 1 and self.input_state.axis_y <= 0:
            self.input_state.prevdir = self.input_state.curdir
            self.input_state.curdir = Direction.South
            self.input_state.key_press |= Key.Down
        elif self.input_state.axis_x == -1 and self.input_state.axis_y >= 0:
            self.input_state.prevdir = self.input_state.curdir
            self.input_state.curdir = Direction.North
            self.input_state.key_press |= Key.Up
        else:
            self.input_state.prevdir = self.input_state.curdir
            self.input_state.curdir = Direction.Unknown
            self.input_state.key_press |= Key.Null
