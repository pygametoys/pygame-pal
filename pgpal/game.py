#! /usr/bin/env python
# -*- coding: utf8 -*-
import atexit
import sys
from threading import Thread
from pgpal import config
from pgpal.compat import pg, range
from pgpal.const import *
from pgpal.utils import pal_x, pal_y, RunResult
from pgpal.battle import BattleFieldMixin, FighterTeamMixin
from pgpal.control import ControllerMixin
from pgpal.ending import EndingTheaterMixin
from pgpal.movie import MoviePlayerMixin
from pgpal.music import MusicPlayerMixin
from pgpal.palette import PalettePainterMixin
from pgpal.player import PlayerManagerMixin
from pgpal.res import ResourceManagerMixin
from pgpal.saves import SaveLoadMixin
from pgpal.scene import SceneLoaderMixin
from pgpal.screen import ScreenDisplayMixin
from pgpal.script import ScriptRunnerMixin
from pgpal.sound import SoundEffectPlayerMixin
from pgpal.text import TextPrinterMixin
from pgpal.uimisc import (
    UIBattleMixin,
    UIMenuMixin,
    UIMixin
)


class InteractiveShell(Thread):
    def __init__(self, game):
        Thread.__init__(self, daemon=True)
        self.game = game
        atexit.register(self.close)

    def run(self):
        ctx_vars = locals()
        ctx_vars['game'] = ctx_vars.pop('self').game
        try:
            from ptpython.repl import embed
            embed(locals=ctx_vars, vi_mode=False)
        except ImportError:
            from code import interact
            interact(local=ctx_vars)

    def close(self):
        try:
            import termios
            fd = sys.stdout.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[0] |= termios.ICRNL
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except ImportError:
            pass


class ChinesePaladin(
    BattleFieldMixin,
    ControllerMixin,
    EndingTheaterMixin,
    FighterTeamMixin,
    MoviePlayerMixin,
    MusicPlayerMixin,
    PalettePainterMixin,
    PlayerManagerMixin,
    ResourceManagerMixin,
    SaveLoadMixin,
    SceneLoaderMixin,
    ScreenDisplayMixin,
    ScriptRunnerMixin,
    SoundEffectPlayerMixin,
    TextPrinterMixin,
    UIMixin,
    UIBattleMixin,
    UIMenuMixin,
):
    def __init__(self):
        for parent_class in self.__class__.__mro__[1:]:
            parent_class.__init__(self)
        if config['show_console']:
            self.console_thread = InteractiveShell(self)
            self.console_thread.start()

    def delay(self, ms):
        till = pg.time.get_ticks() + ms
        self.delay_until(till)

    def delay_until(self, till):
        self.process_event()
        while pg.time.get_ticks() < till:
            pg.time.delay(1)
            self.process_event()

    def shutdown(self, status=None):
        self.quit_music()
        pg.quit()
        sys.exit(status)

    def start(self):
        self.load_flags |= (LoadResFlag.Scene | LoadResFlag.PlayerSprite)
        if not self.entering_scene:
            self.play_music(self.num_music, True, 1)
        self.need_fadein = True
        self.frame_num = 0

    def start_frame(self):
        self.update(True)
        if self.entering_scene:
            return
        self.update_party()
        self.make_scene()
        self.update_screen()
        if self.input_state.key_press & Key.Menu:
            self.ingame_menu()
        elif self.input_state.key_press & Key.UseItem:
            self.use_item()
        elif self.input_state.key_press & Key.ThrowItem:
            self.equip_item()
        elif self.input_state.key_press & Key.Force:
            self.ingame_magic_menu()
        elif self.input_state.key_press & Key.Status:
            self.show_player_status()
        elif self.input_state.key_press & Key.Search:
            self.search()
        elif self.input_state.key_press & Key.Flee:
            self.quit()
        self.chasespeed_change_cycles -= 1
        self.chasespeed_change_cycles &= 0xFFFF
        if self.chasespeed_change_cycles == 0:
            self.chase_range = 1

    def update(self, trigger):
        if trigger:
            if self.entering_scene:
                self.entering_scene = False
                i = self.num_scene - 1
                self.scenes[i].script_on_enter = self.run_trigger_script(
                    self.scenes[i].script_on_enter, 0xFFFF
                )
                if self.entering_scene or self.to_start:
                    return
                self.clear_key_state()
                self.make_scene()
            for event_object_id in range(len(self.event_objects)):
                p = self.event_objects[event_object_id]
                if p.vanish_time != 0:
                    p.vanish_time += 1 if p.vanish_time < 0 else -1
            for event_object_id in range(
                self.scenes[self.num_scene - 1].event_object_index + 1,
                self.scenes[self.num_scene].event_object_index + 1,
            ):
                p = self.event_objects[event_object_id - 1]
                if p.vanish_time != 0:
                    continue
                if p.state < 0:
                    if (
                        p.x < pal_x(self.viewport) or
                        p.x > pal_x(self.viewport) + 320 or
                        p.y < pal_y(self.viewport) or
                        p.y > pal_y(self.viewport) + 320
                    ):
                        p.state = abs(p.state)
                        p.current_frame_num = 0
                elif p.state > 0 and p.trigger_mode >= TriggerMode.TouchNear:
                    if (
                        abs(pal_x(self.viewport) + pal_x(self.partyoffset) - p.x) +
                        abs(pal_y(self.viewport) + pal_y(self.partyoffset) - p.y) * 2 <
                        (p.trigger_mode - TriggerMode.TouchNear) * 32 + 16
                    ):
                        if p.sprite_frames_num:
                            p.current_frame_num = 0
                            x_offset = pal_x(self.viewport) + \
                                       pal_x(self.partyoffset) - p.x
                            y_offset = pal_y(self.viewport) + \
                                       pal_y(self.partyoffset) - p.y
                            if x_offset > 0:
                                p.direction = Direction.East if y_offset > 0 else Direction.North
                            else:
                                p.direction = Direction.South if y_offset > 0 else Direction.West
                            self.update_party_gestures(False)
                            self.make_scene()
                            self.update_screen()
                        p.trigger_script = self.run_trigger_script(p.trigger_script, event_object_id)
                        self.clear_key_state()
                        if self.entering_scene or self.to_start:
                            return
        for event_object_id in range(
            self.scenes[self.num_scene - 1].event_object_index + 1,
            self.scenes[self.num_scene].event_object_index + 1,
        ):
            p = self.event_objects[event_object_id - 1]
            if p.state > 0 and p.vanish_time == 0:
                script_entry = p.auto_script
                if script_entry != 0:
                    p.auto_script = self.run_auto_script(script_entry, event_object_id)
                    if self.entering_scene or self.to_start:
                        return
            if (
                trigger and
                p.state >= ObjectState.Blocker and
                p.sprite_num != 0 and
                abs(p.x - pal_x(self.viewport) - pal_x(self.partyoffset)) +
                abs(p.y - pal_y(self.viewport) - pal_y(self.partyoffset)) * 2 <= 12
            ):
                direction = (p.direction + 1) % 4
                for i in range(4):
                    x = pal_x(self.viewport) + pal_x(self.partyoffset)
                    y = pal_y(self.viewport) + pal_y(self.partyoffset)
                    x += -16 if direction in {Direction.West, Direction.South} else 16
                    y += -8 if direction in {Direction.West, Direction.North} else 8
                    pos = x, y
                    if not self.check_obstacle(pos, True, 0):
                        self.viewport = (
                            x - pal_x(self.partyoffset),
                            y - pal_y(self.partyoffset)
                        )
                        break
                    direction = (direction + 1) % 4
        self.frame_num += 1

    def use_item(self):
        while True:
            obj = self.item_select_menu(ItemFlag.Usable)
            if obj == 0:
                return
            if not (self.objects[obj].item.flags & ItemFlag.ApplyToAll):
                player = 0
                while True:
                    player = self.item_use_menu(obj)
                    if player == MENUITEM_VALUE_CANCELLED:
                        break
                    self.objects[obj].item.script_on_use = self.run_trigger_script(
                        self.objects[obj].item.script_on_use, player
                    )
                    if (self.objects[obj].item.flags & ItemFlag.Consuming) and RunResult.success:
                        self.add_item_to_inventory(obj, -1)
            else:
                self.objects[obj].item.script_on_use = self.run_trigger_script(
                    self.objects[obj].item.script_on_use, 0xFFFF
                )
                if (self.objects[obj].item.flags & ItemFlag.Consuming) and RunResult.success:
                    self.add_item_to_inventory(obj, -1)
                return

    def equip_item(self):
        while True:
            obj = self.item_select_menu(ItemFlag.Equipable)
            if obj == 0:
                return
            self.equip_item_menu(obj)

    def search(self):
        x = pal_x(self.viewport) + pal_x(self.partyoffset)
        y = pal_y(self.viewport) + pal_y(self.partyoffset)
        x_offset = 16 if self.party_direction in {
            Direction.North, Direction.East
        } else -16
        y_offset = 8 if self.party_direction in {
            Direction.South, Direction.East
        } else -8
        pos = [(x, y)]
        for i in range(4):
            pos.extend(
                [
                    (x + x_offset, y + y_offset),
                    (x, y + y_offset * 2),
                    (x + x_offset, y),
                ]
            )
            x += x_offset
            y += y_offset
        for i in range(13):
            dh = bool(pal_x(pos[i]) % 32)
            dx = pal_x(pos[i]) // 32
            dy = pal_y(pos[i]) // 16
            for k in range(
                self.scenes[self.num_scene - 1].event_object_index,
                self.scenes[self.num_scene].event_object_index
            ):
                p = self.event_objects[k]
                ex = p.x // 32
                ey = p.y // 16
                eh = bool(p.x % 32)
                if p.state <= 0:
                    continue
                elif p.trigger_mode >= TriggerMode.TouchNear:
                    continue
                elif p.trigger_mode * 6 - 4 < i:
                    continue
                elif not (dx == ex and dy == ey and dh == eh):
                    continue
                if p.sprite_frames_num * 4 > p.current_frame_num:
                    p.current_frame_num = 0
                    p.direction = (self.party_direction + 2) % 4
                    for l in range(self.max_party_member_index + 1):
                        self.party[l].frame = self.party_direction * 3
                    self.make_scene()
                    self.update_screen()
                p.trigger_script = self.run_trigger_script(p.trigger_script, k + 1)
                self.delay(50)
                self.clear_key_state()
                return
