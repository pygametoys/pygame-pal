#! /usr/bin/env python
# -*- coding: utf8 -*-
from collections import deque
from itertools import chain
from operator import attrgetter
import random
import attr
from pgpal.compat import range, partialmethod
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.mkfext import ABC, F, Fire, SubPlace
from pgpal.player import PoisonStatus
from pgpal.res import Enemy
from pgpal.uimisc import MenuItem
from pgpal.utils import short, pal_x, pal_y, RunResult, WORD


@attr.s(slots=True)
class ShowNum(object):
    num = attr.ib(factory=int)
    pos = attr.ib(default=(0, 0))
    time = attr.ib(factory=int)
    color = attr.ib(converter=NumColor, default=1)


@attr.s(slots=True)
class Summon(object):
    sprite = attr.ib(default=None)
    current_frame = attr.ib(factory=int)


@attr.s
class BattleAction(object):
    action_type = attr.ib(converter=BattleActionType, default=0)
    action_id = attr.ib(factory=int)
    target = attr.ib(factory=int)
    remaining_time = attr.ib(factory=float)


@attr.s
class ActionItem(object):
    _dexterity = attr.ib(converter=int)
    index = attr.ib(factory=int)
    is_enemy = attr.ib(factory=bool)

    @property
    def dexterity(self):
        return self._dexterity

    @dexterity.setter
    def dexterity(self, value):
        self._dexterity = int(round(value))


@attr.s
class BattleEnemy(object):
    object_id = attr.ib(factory=int)
    e = attr.ib(default=Enemy(None))
    status = attr.ib(
        converter=WORD * Status.All, default=None
    )
    poisons = attr.ib(
        converter=PoisonStatus * MAX_POISONS, default=None
    )
    sprite = attr.ib(default=None)
    pos = attr.ib(default=(0, 0))
    pos_original = attr.ib(default=(0, 0))
    current_frame = attr.ib(factory=int)
    state = attr.ib(converter=FighterState, default=0)
    turn_start = attr.ib(factory=bool)
    first_move_done = attr.ib(factory=bool)
    dual_move = attr.ib(factory=bool)
    script_on_turn_start = attr.ib(factory=int)
    script_on_battle_end = attr.ib(factory=int)
    script_on_ready = attr.ib(factory=int)
    prev_hp = attr.ib(factory=int)
    color_shift = attr.ib(factory=int)


@attr.s
class BattlePlayer(object):
    color_shift = attr.ib(factory=int)
    time_meter = attr.ib(factory=float)
    hiding_time = attr.ib(factory=int)
    sprite = attr.ib(default=None)
    pos = attr.ib(default=(0, 0))
    pos_original = attr.ib(default=(0, 0))
    current_frame = attr.ib(factory=int)
    state = attr.ib(converter=FighterState, default=0)
    action = attr.ib(factory=BattleAction)
    prev_action = attr.ib(factory=BattleAction)
    defending = attr.ib(factory=bool)
    prev_hp = attr.ib(factory=int)
    prev_mp = attr.ib(factory=int)


@attr.s
class BattleUI(object):
    state = attr.ib(converter=BattleUIState, default=0)
    menu_state = attr.ib(converter=BattleMenuState, default=0)
    msg = attr.ib(factory=str)
    next_msg = attr.ib(factory=str)
    msg_show_time = attr.ib(factory=int)
    next_msg_duration = attr.ib(factory=int)

    cur_player_index = attr.ib(factory=int)
    selected_action = attr.ib(factory=int)
    selected_index = attr.ib(factory=int)
    prev_enemy_target = attr.ib(factory=int)

    action_type = attr.ib(factory=int)
    object_id = attr.ib(factory=int)
    auto_attack = attr.ib(factory=bool)

    show_nums = attr.ib(default=[ShowNum() for _ in range(BATTLEUI_MAX_SHOWNUM)])


@attr.s
class Battle(object):
    players = attr.ib(default=[BattlePlayer() for _ in range(MAX_PLAYERS_IN_PARTY)])
    enemies = attr.ib(default=[BattleEnemy() for _ in range(MAX_ENEMIES_IN_TEAM)])

    max_enemy_index = attr.ib(factory=int)

    scene_buf = attr.ib(default=None)
    background = attr.ib(default=None)

    background_color_shift = attr.ib(factory=int)

    summon_sprite = attr.ib(default=None)
    pos_summon = attr.ib(default=(0, 0))
    summon_frame = attr.ib(factory=int)

    exp_gained = attr.ib(factory=int)
    cash_gained = attr.ib(factory=int)

    is_boss = attr.ib(factory=bool)
    enemy_cleared = attr.ib(factory=bool)
    battle_result = attr.ib(converter=BattleResult, default=0)

    ui = attr.ib(factory=BattleUI)

    effect_sprite = attr.ib(default=None)

    enemy_moving = attr.ib(factory=int)

    hiding_time = attr.ib(factory=int)

    moving_player_index = attr.ib(factory=int)

    blow = attr.ib(factory=int)

    phase = attr.ib(converter=BattlePhase, default=0)
    action_queue = attr.ib(default=deque([], MAX_ACTIONQUEUE_ITEMS))
    repeat = attr.ib(factory=bool)
    force = attr.ib(factory=bool)
    flee = attr.ib(factory=bool)
    prev_auto_atk = attr.ib(factory=bool)
    prev_player_auto_atk = attr.ib(factory=bool)


class BattleFieldMixin(object):
    def __init__(self):
        self.in_battle = False
        self.auto_battle = False
        self.num_battle_field = 0
        self.battle = Battle()
        self.abc = ABC()
        self.f = F()

    def battle_player_escape(self):
        self.play_sound(45)
        self.battle_update_fighters()
        for i in range(self.max_party_member_index + 1):
            player_role = self.party[i].player_role
            if self.player_roles.hp[player_role] > 0:
                self.battle.players[i].current_frame = 0
        for i in range(16):
            for j in range(self.max_party_member_index + 1):
                player = self.battle.players[j]
                player_role = self.party[j].player_role
                if self.player_roles.hp[player_role] > 0:
                    if j == 0:
                        player.pos = (
                            pal_x(player.pos) + 4,
                            pal_y(player.pos) +
                            (6 if self.max_party_member_index > 0 else 4)
                        )
                    elif j == 1:
                        player.pos = (
                            pal_x(player.pos) + 4,
                            pal_y(player.pos) + 4
                        )
                    elif j == 2:
                        player.pos = (
                            pal_x(player.pos) + 6,
                            pal_y(player.pos) + 3
                        )
            self.battle_delay(1, 0, False)
        for i in range(self.max_party_member_index + 1):
            self.battle.players[i].pos = 9999, 9999
        self.battle_delay(1, 0, False)
        self.battle.battle_result = BattleResult.Fleed

    def battle_enemy_escape(self):
        f = True
        while f:
            f = False
            for j in range(self.battle.max_enemy_index + 1):
                enemy = self.battle.enemies[j]
                if enemy.object_id == 0:
                    continue
                enemy.pos = pal_x(enemy.pos) - 5, pal_y(enemy.pos)
                w = enemy.sprite[0].width
                if pal_x(enemy.pos) + w > 0:
                    f = True
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            self.update_screen()
            self.delay(10)
        self.delay(500)
        self.battle.battle_result = BattleResult.Terminated

    @staticmethod
    def check_hidden_exp(
        exp_name,
        stat_name,
        label,
        self=0,
        total_count=0,
        w=0,
        orig_player_roles=0,
        rect=0,
        offset_x=0,
        max_name_width=0,
        max_property_width=0,
        **kwargs
    ):
        exp = self.battle.exp_gained
        exp *= getattr(self.exp, exp_name)[w].count
        exp //= total_count
        exp *= 2
        exp += getattr(self.exp, exp_name)[w].exp
        if getattr(self.exp, exp_name)[w].level > MAX_LEVELS:
            getattr(self.exp, exp_name)[w].level = MAX_LEVELS
        while exp >= self.level_up_exp[getattr(self.exp, exp_name)[w].level]:
            exp -= self.level_up_exp[getattr(self.exp, exp_name)[w].level]
            getattr(self.player_roles, stat_name)[w] += random.randint(1, 2)
            if getattr(self.exp, exp_name)[w].level <= MAX_LEVELS:
                getattr(self.exp, exp_name)[w].level += 1
        getattr(self.exp, exp_name)[w].exp = exp
        if getattr(self.player_roles, stat_name)[w] != getattr(orig_player_roles, stat_name)[w]:
            buf = self.words[self.player_roles.name[w]] + self.words[label] + self.words[BATTLEWIN_LEVELUP_LABEL]
            self.one_line_box(
                (offset_x + 78, 60),
                max_name_width + max_property_width +
                self.text_width(self.words[BATTLEWIN_LEVELUP_LABEL]) // 32 + 4, False
            )
            self.draw_text(
                buf, (offset_x + 90, 70), 0,
                False, False
            )
            self.draw_number(
                getattr(self.player_roles, stat_name)[w] - getattr(orig_player_roles, stat_name)[w],
                5, (183 + (max_name_width + max_property_width - 3) * 8, 74),
                NumColor.Yellow, NumAlign.Right
            )
            self.update_screen(rect)
            self.wait_for_key(3000)

    def battle_won(self):
        rect = pg.Rect(0, 60, 320, 100)
        rect1 = pg.Rect(80, 0, 180, 200)
        orig_player_roles = self.player_roles.copy()
        self.screen_bak.blit(self.screen, (0, 0))
        if self.battle.exp_gained > 0:
            w1 = self.word_width(BATTLEWIN_GETEXP_LABEL) + 3
            ww1 = (w1 - 8) << 3
            self.play_music(2 if self.battle.is_boss else 3, False)
            self.one_line_box((83 - ww1, 60), w1, False)
            self.one_line_box((65, 105), 10, False)
            self.draw_text(
                self.words[BATTLEWIN_GETEXP_LABEL],
                (95 - ww1, 70), 0, False, False
            )
            self.draw_text(
                self.words[BATTLEWIN_BEATENEMY_LABEL],
                (77, 115), 0, False, False
            )
            self.draw_text(
                self.words[BATTLEWIN_DOLLAR_LABEL],
                (197, 115), 0, False, False
            )
            self.draw_number(
                self.battle.exp_gained, 5, (182 + ww1, 74),
                NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.battle.cash_gained, 5, (162, 119),
                NumColor.Yellow, NumAlign.Mid
            )
            self.update_screen(rect)
            self.wait_for_key(5500 if self.battle.is_boss else 3000)
        self.cash += self.battle.cash_gained
        fake_menu_items = [
            MenuItem(
                i + 1, self.words[self.player_roles.name[i]],
                True, (0, 0)
            ) for i in range(6)
        ]
        max_name_width = self.menu_text_max_width(fake_menu_items)
        fake_menu_items2 = [
            MenuItem(
                i + 1, self.words[_label],
                True, (0, 0)
            ) for i, _label in enumerate([
                STATUS_LABEL_LEVEL,
                STATUS_LABEL_HP,
                STATUS_LABEL_MP,
                STATUS_LABEL_ATTACKPOWER,
                STATUS_LABEL_MAGICPOWER,
                STATUS_LABEL_RESISTANCE,
                STATUS_LABEL_DEXTERITY,
                STATUS_LABEL_FLEERATE
            ])
        ]
        max_property_width = self.menu_text_max_width(fake_menu_items2)
        property_length = max_property_width - 1
        offset_x = -8 * property_length
        rect1.x += offset_x
        rect1.w -= 2 * offset_x
        for i in range(self.max_party_member_index + 1):
            level_up = False
            w = self.party[i].player_role
            if self.player_roles.hp[w] == 0:
                continue
            exp = self.exp.primary_exp[w].exp
            exp += self.battle.exp_gained
            if self.player_roles.level[w] > MAX_LEVELS:
                self.player_roles.level[w] = MAX_LEVELS
            while exp >= self.level_up_exp[self.player_roles.level[w]]:
                exp -= self.level_up_exp[self.player_roles.level[w]]
                if self.player_roles.level[w] < MAX_LEVELS:
                    level_up = True
                    self.player_level_up(w, 1)
                    self.player_roles.hp[w] = self.player_roles.max_hp[w]
                    self.player_roles.mp[w] = self.player_roles.max_mp[w]
            self.exp.primary_exp[w].exp = exp
            if level_up:
                self.blit(self.screen_bak, (0, 0))
                self.one_line_box((offset_x + 80, 0), property_length + 10, False)
                self.create_box((offset_x + 82, 32), 7, property_length + 8, 1, False)
                buffer = (
                        self.words[self.player_roles.name[w]] +
                        self.words[STATUS_LABEL_LEVEL] +
                        self.words[BATTLEWIN_LEVELUP_LABEL]
                )
                self.draw_text(
                    buffer, (110, 10), 0,
                    False, False
                )
                for j in range(8):
                    self.sprite_ui[SPRITENUM_ARROW].blit_to(
                        self.screen, (-offset_x + 180, 48 + 18 * j)
                    )
                for i, item in enumerate(fake_menu_items2):
                    self.draw_text(
                        item.label, (offset_x + 100, 44 + 18 * i),
                        BATTLEWIN_LEVELUP_LABEL, True, False
                    )
                self.draw_number(
                    orig_player_roles.level[w], 4,
                    (-offset_x + 133, 47), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    self.player_roles.level[w], 4,
                    (-offset_x + 195, 47), NumColor.Yellow, NumAlign.Right
                )

                self.draw_number(
                    orig_player_roles.hp[w], 4,
                    (-offset_x + 133, 64), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    orig_player_roles.max_hp[w], 4,
                    (-offset_x + 154, 68), NumColor.Blue, NumAlign.Right
                )
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (-offset_x + 156, 66)
                )
                self.draw_number(
                    self.player_roles.hp[w], 4,
                    (-offset_x + 195, 64), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    self.player_roles.max_hp[w], 4,
                    (-offset_x + 216, 68), NumColor.Blue, NumAlign.Right
                )
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (-offset_x + 218, 66)
                )

                self.draw_number(
                    orig_player_roles.mp[w], 4,
                    (-offset_x + 133, 82), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    orig_player_roles.max_mp[w], 4,
                    (-offset_x + 154, 86), NumColor.Blue, NumAlign.Right
                )
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (-offset_x + 156, 84)
                )
                self.draw_number(
                    self.player_roles.mp[w], 4,
                    (-offset_x + 195, 82), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    self.player_roles.max_mp[w], 4,
                    (-offset_x + 216, 86), NumColor.Blue, NumAlign.Right
                )
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (-offset_x + 218, 84)
                )

                for i, name in enumerate([
                    'attack_strength',
                    'magic_strength',
                    'defense',
                    'dexterity',
                    'flee_rate'
                ]):
                    self.draw_number(
                        getattr(orig_player_roles, name)[w] +
                        self.get_player_stat(w, name) -
                        getattr(self.player_roles, name)[w], 4,
                        (-offset_x + 133, 101 + i * 18),
                        NumColor.Yellow, NumAlign.Right
                    )
                    self.draw_number(
                        self.get_player_stat(w, name), 4,
                        (-offset_x + 195, 101 + i * 18),
                        NumColor.Yellow, NumAlign.Right
                    )
                self.update_screen(rect1)
                self.wait_for_key(3000)
                orig_player_roles = self.player_roles.copy()
            total_count = 0
            total_count += self.exp.attack_exp[w].count
            total_count += self.exp.defense_exp[w].count
            total_count += self.exp.dexterity_exp[w].count
            total_count += self.exp.flee_exp[w].count
            total_count += self.exp.health_exp[w].count
            total_count += self.exp.magic_exp[w].count
            total_count += self.exp.magic_power_exp[w].count
            if total_count > 0:
                self.check_hidden_exp('health_exp', 'max_hp', STATUS_LABEL_HP, **locals())
                self.check_hidden_exp('magic_exp', 'max_mp', STATUS_LABEL_MP, **locals())
                self.check_hidden_exp('attack_exp', 'attack_strength', STATUS_LABEL_ATTACKPOWER, **locals())
                self.check_hidden_exp('magic_power_exp', 'magic_strength', STATUS_LABEL_MAGICPOWER, **locals())
                self.check_hidden_exp('defense_exp', 'defense', STATUS_LABEL_RESISTANCE, **locals())
                self.check_hidden_exp('dexterity_exp', 'dexterity', STATUS_LABEL_DEXTERITY, **locals())
                self.check_hidden_exp('flee_exp', 'flee_rate', STATUS_LABEL_FLEERATE, **locals())
            j = 0
            while j < len(self.level_up_magics):
                if (
                    self.level_up_magics[j][w].magic == 0 or
                    self.level_up_magics[j][w].level > self.player_roles.level[w]
                ):
                    j += 1
                    continue
                if self.add_magic(w, self.level_up_magics[j][w].magic):
                    w1 = max(self.word_width(self.player_roles.name[w]), 3)
                    w2 = max(self.word_width(BATTLEWIN_ADDMAGIC_LABEL), 2)
                    w3 = max(self.word_width(self.level_up_magics[j][w].magic), 5)
                    ww = (w1 + w2 + w3 - 10) << 3
                    self.one_line_box(
                        (65 - ww, 105), w1 + w2 + w3, False
                    )
                    self.draw_text(
                        self.words[self.player_roles.name[w]],
                        (75 - ww, 115), 0, False, False
                    )
                    self.draw_text(
                        self.words[BATTLEWIN_ADDMAGIC_LABEL],
                        (75 + 16 * w1 - ww, 115), 0, False, False
                    )
                    self.draw_text(
                        self.words[self.level_up_magics[j][w].magic],
                        (75 + 16 * (w1 + w2) - ww, 115), 0x1B, False, False
                    )
                    self.update_screen(rect)
                    self.wait_for_key(3000)
                j += 1
        for i in range(self.battle.max_enemy_index + 1):
            self.run_trigger_script(
                self.battle.enemies[i].script_on_battle_end, i
            )
        for i in range(self.max_party_member_index + 1):
            w = self.party[i].player_role
            self.player_roles.hp[w] += (self.player_roles.max_hp[w] - self.player_roles.hp[w]) // 2
            self.player_roles.mp[w] += (self.player_roles.max_mp[w] - self.player_roles.mp[w]) // 2

    def battle_fade_scene(self):
        index = [0, 3, 1, 5, 2, 4]
        ticks = pg.time.get_ticks()
        for i in range(12):
            for j in range(6):
                self.delay_until(ticks)
                ticks = pg.time.get_ticks() + 16
                self.battle.scene_buf.lock()
                self.screen_bak.lock()
                buf_scene = pg.PixelArray(self.battle.scene_buf)
                buf_bak = pg.PixelArray(self.screen_bak)
                y = 0
                x = index[j]
                while y < 200:
                    a = buf_scene[x, y]
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
                del buf_scene
                del buf_bak
                self.battle.scene_buf.unlock()
                self.screen_bak.unlock()
                self.blit(self.screen_bak, (0, 0))
                self.battle_ui_update()
                self.update_screen()
        self.blit(self.battle.scene_buf, (0, 0))
        self.battle_ui_update()
        self.update_screen()

    def battle_make_scene(self):
        src = pg.PixelArray(self.battle.background)
        dst = pg.PixelArray(self.battle.scene_buf)
        for y in range(200):
            for x in range(320):
                b = src[x, y] & 0x0F
                b += self.battle.background_color_shift
                if b & 0x80:
                    b = 0
                elif b & 0x70:
                    b = 0x0F
                dst[x, y] = b | (src[x, y] & 0xF0)
        self.battle.background.unlock()
        self.battle.scene_buf.unlock()
        self.apply_wave(self.battle.scene_buf)
        for i in range(self.battle.max_enemy_index, -1, -1):
            enemy = self.battle.enemies[i]
            pos = self.battle.enemies[i].pos
            if (
                enemy.status[Status.Confused] > 0 and
                enemy.status[Status.Sleep] == 0 and
                enemy.status[Status.Paralyzed] == 0
            ):
                pos = pal_x(pos) + random.randint(-1, 1), pal_y(pos)
            if enemy.object_id != 0 and enemy.sprite is not None:
                pos = (
                    pal_x(pos) - enemy.sprite[enemy.current_frame].width // 2,
                    pal_y(pos) - enemy.sprite[enemy.current_frame].height
                )
                if enemy.color_shift:
                    enemy.sprite[enemy.current_frame].blit_with_color_shift(
                        self.battle.scene_buf, pos, enemy.color_shift
                    )
                else:
                    enemy.sprite[enemy.current_frame].blit_to(
                        self.battle.scene_buf, pos
                    )
        if self.battle.summon_sprite is not None:
            pos = (
                pal_x(self.battle.pos_summon) - self.battle.summon_sprite[self.battle.summon_frame].width // 2,
                pal_y(self.battle.pos_summon) - self.battle.summon_sprite[self.battle.summon_frame].height,
            )
            self.battle.summon_sprite[self.battle.summon_frame].blit_to(
                self.battle.scene_buf, pos
            )
        else:
            for i in range(self.max_party_member_index + 1):
                player = self.battle.players[i]
                pos = player.pos
                w = self.party[i].player_role
                if (
                    self.player_status[w][Status.Confused] != 0 and
                    self.player_status[w][Status.Sleep] == 0 and
                    self.player_status[w][Status.Paralyzed] == 0 and
                    self.player_roles.hp[w] > 0
                ):
                    continue
                pos = (
                    pal_x(pos) - player.sprite[player.current_frame].width // 2,
                    pal_y(pos) - player.sprite[player.current_frame].height
                )
                if player.color_shift != 0:
                    player.sprite[player.current_frame].blit_with_color_shift(
                        self.battle.scene_buf, pos, player.color_shift
                    )
                elif self.battle.hiding_time == 0:
                    player.sprite[player.current_frame].blit_to(
                        self.battle.scene_buf, pos
                    )
            for i in range(self.max_party_member_index, -1, -1):
                player = self.battle.players[i]
                pos = player.pos
                w = self.party[i].player_role
                if (
                    self.player_status[w][Status.Confused] != 0 and
                    self.player_status[w][Status.Sleep] == 0 and
                    self.player_status[w][Status.Paralyzed] == 0 and
                    self.player_roles.hp[w] > 0
                ):
                    pos = pal_x(pos), pal_y(pos) + random.randint(-1, 1)    
                    pos = (
                        pal_x(pos) - player.sprite[player.current_frame].width // 2,
                        pal_y(pos) - player.sprite[player.current_frame].height
                    )
                    if player.color_shift != 0:
                        player.sprite[player.current_frame].blit_with_color_shift(
                            self.battle.scene_buf, pos, player.color_shift
                        )
                    elif self.battle.hiding_time == 0:
                        player.sprite[player.current_frame].blit_to(
                            self.battle.scene_buf, pos
                        )

    def battle_main(self):
        self.screen_bak.blit(self.screen, (0, 0))
        self.battle_make_scene()
        self.blit(self.battle.scene_buf, (0, 0))
        self.play_music(0, False, 1)
        self.delay(200)
        self.switch_screen(5)
        self.play_music(self.num_battle_music, True)
        if self.need_fadein:
            self.fadein(1)
            self.need_fadein = False
        for i in range(self.battle.max_enemy_index + 1):
            self.battle.enemies[i].script_on_turn_start = self.run_trigger_script(
                self.battle.enemies[i].script_on_turn_start, i
            )
            if self.battle.battle_result != BattleResult.PreBattle:
                break
        if self.battle.battle_result == BattleResult.PreBattle:
            self.battle.battle_result = BattleResult.OnGoing
        ticks = pg.time.get_ticks()
        while True:
            if self.battle.battle_result != BattleResult.OnGoing:
                break
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
            self.battle_start_frame()
            self.update_screen()
        return self.battle.battle_result

    def load_battle_sprites(self):
        self.free_battle_sprites()
        for i in range(self.max_party_member_index + 1):
            s = self.get_player_battle_sprite(self.party[i].player_role)
            if self.f[s] is None:
                continue
            self.battle.players[i].sprite = self.f[s]
            pos = player_pos[self.max_party_member_index][i]
            self.battle.players[i].pos_original = pos
            self.battle.players[i].pos = pos
        for i in range(self.battle.max_enemy_index + 1):
            if self.battle.enemies[i].object_id == 0:
                continue
            s = self.objects[self.battle.enemies[i].object_id].enemy.enemy_id
            if self.abc[s] is None:
                continue
            self.battle.enemies[i].sprite = self.abc[s]
            x = self.enemy_pos.pos[i][self.battle.max_enemy_index].x
            y = self.enemy_pos.pos[i][self.battle.max_enemy_index].y
            y += self.battle.enemies[i].e.y_pos_offset
            self.battle.enemies[i].pos_original = x, y
            self.battle.enemies[i].pos = x, y

    def load_battle_background(self):
        self.battle.background = self.create_compatible_surface(self.screen)
        self.fbp.render(
            self.num_battle_field,
            self.battle.background
        )

    def free_battle_sprites(self):
        for i in range(self.max_party_member_index + 1):
            self.battle.players[i].sprite = None
        for i in range(self.battle.max_enemy_index + 1):
            self.battle.enemies[i].sprite = None
        self.battle.summon_sprite = None

    def start_battle(self, enemy_team, is_boss):
        prev_wave_level = self.screen_wave
        prev_wave_progression = self.wave_progression

        self.wave_progression = 0
        self.screen_wave = self.battle_fields[self.num_battle_field].screen_wave

        for i in range(self.max_party_member_index + 1):
            w = self.party[i].player_role
            if self.player_roles.hp[w] == 0:
                self.player_roles.hp[w] = 1
                self.player_status[w][Status.Puppet] = 0
                for _, fieldname in self.exp._fields_[1:]:
                    getattr(self.exp, fieldname)[w].count = 0
        for i in range(MAX_INVENTORY):
            self.inventory[i].amount_in_use = 0
        i = 0
        while i < MAX_ENEMIES_IN_TEAM:
            self.battle.enemies[i] = BattleEnemy()
            w = self.enemy_team[enemy_team][i]
            if w == 0xFFFF:
                break
            if w != 0:
                self.battle.enemies[i].e = self.enemies[self.objects[w].enemy.enemy_id].copy()
                self.battle.enemies[i].object_id = w
                self.battle.enemies[i].state = FighterState.Wait
                self.battle.enemies[i].script_on_turn_start = self.objects[w].enemy.script_on_turn_start
                self.battle.enemies[i].script_on_battle_end = self.objects[w].enemy.script_on_battle_end
                self.battle.enemies[i].script_on_ready = self.objects[w].enemy.script_on_ready
                self.battle.enemies[i].color_shift = 0
            i += 1
        self.battle.max_enemy_index = i - 1
        for i in range(self.max_party_member_index + 1):
            self.battle.players[i].time_meter = 15.0
            self.battle.players[i].hiding_time = 0
            self.battle.players[i].state = FighterState.Wait
            self.battle.players[i].defending = False
            self.battle.players[i].current_frame = 0
            self.battle.players[i].color_shift = False
        self.load_battle_sprites()
        self.load_battle_background()
        self.battle.scene_buf = self.create_compatible_surface(self.screen)
        self.update_equipments()
        self.battle.exp_gained = 0
        self.battle.cash_gained = 0
        self.battle.is_boss = is_boss
        self.battle.enemy_cleared = False
        self.battle.enemy_moving = False
        self.battle.hiding_time = 0
        self.battle.moving_player_index = 0

        self.battle.ui.msg = ''
        self.battle.ui.next_msg = ''
        self.battle.ui.msg_show_time = 0
        self.battle.ui.state = BattleUIState.Wait
        self.battle.ui.auto_attack = False
        self.battle.ui.selected_index = 0
        self.battle.ui.prev_enemy_target = -1

        self.battle.ui.show_nums = [
            ShowNum() for _ in range(BATTLEUI_MAX_SHOWNUM)
        ]

        self.battle.ui.summon_sprite = None
        self.battle.ui.background_color_shift = 0

        self.in_battle = True
        self.battle.battle_result = BattleResult.PreBattle

        self.battle_update_fighters()
        self.battle.effect_sprite = SubPlace(self.data.read(10))
        self.battle.phase = BattlePhase.SelectAction
        self.battle.repeat = False
        self.battle.force = False
        self.battle.flee = False
        self.battle.prev_auto_atk = False

        i = self.battle_main()
        if i == BattleResult.Won:
            self.battle_won()
        for w in range(MAX_INVENTORY):
            self.inventory[w].amount_in_use = 0
        self.clear_all_player_status()
        for w in range(MAX_PLAYER_ROLES):
            self.cure_poison_by_level(w, 3)
            self.remove_equipment_effect(w, BodyPart.Extra)

        self.free_battle_sprites()
        self.battle.effect_sprite = None
        self.battle.background = None
        self.battle.scene_buf = None
        self.in_battle = False
        self.play_music(self.num_music, True, 1)

        self.screen_wave = prev_wave_level
        self.wave_progression = prev_wave_progression
        return i


class FighterTeamMixin(object):
    def __init__(self):
        self._invincible = False
        self.fire = Fire()

    def battle_post_action_check(self, check_players):
        fade = False
        enemy_remaining = False
        for i in range(self.battle.max_enemy_index + 1):
            enemy = self.battle.enemies[i]
            if enemy.object_id == 0:
                continue
            if enemy.e.health <= 0:
                self.battle.exp_gained += enemy.e.exp
                self.battle.cash_gained += enemy.e.cash
                self.play_sound(enemy.e.death_sound)
                enemy.object_id = 0
                fade = True
                continue
            enemy_remaining = True
        if not enemy_remaining:
            self.battle.enemy_cleared = True
            self.battle.ui.state = BattleUIState.Wait
        if check_players and not self.auto_battle:
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                if (
                    self.player_roles.hp[w] < self.battle.players[i].prev_hp and
                    self.player_roles.hp[w] == 0
                ):
                    w = self.player_roles.covered_by[w]
                    j = 0
                    while j <= self.max_party_member_index:
                        if self.party[j].player_role == w:
                            break
                        j += 1
                    if (
                        self.player_roles.hp[w] > 0 and
                        self.player_status[w][Status.Sleep] == 0 and
                        self.player_status[w][Status.Paralyzed] == 0 and
                        self.player_status[w][Status.Confused] == 0 and
                        j <= self.max_party_member_index
                    ):
                        name = self.player_roles.name[w]
                        if self.objects[name].player.script_on_friend_death != 0:
                            self.battle_delay(10, 0, True)
                            self.battle_make_scene()
                            self.blit(self.battle.scene_buf, (0, 0))
                            self.update_screen()
                            self.battle.battle_result = BattleResult.Pause
                            self.objects[name].player.script_on_friend_death = self.run_trigger_script(
                                self.objects[name].player.script_on_friend_death, w
                            )
                            self.battle.battle_result = BattleResult.OnGoing
                            self.clear_key_state()
                            return self.battle_post_action_check_end(fade)
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                if (
                    self.player_status[w][Status.Sleep] != 0 or
                    self.player_status[w][Status.Confused] != 0
                ):
                    continue
                if self.player_roles.hp[w] < self.battle.players[i].prev_hp:
                    if (
                        self.player_roles.hp[w] > 0 and self.is_player_dying(w) and
                        self.battle.players[i].prev_hp >= self.player_roles.max_hp[w] // 5
                    ):
                        cover = self.player_roles.covered_by[w]
                        if (
                            self.player_status[cover][Status.Sleep] != 0 or
                            self.player_status[cover][Status.Paralyzed] != 0 or
                            self.player_status[cover][Status.Confused] != 0
                        ):
                            continue
                        name = self.player_roles.name[w]
                        self.play_sound(self.player_roles.dying_sound[w])
                        j = 0
                        while j <= self.max_party_member_index:
                            if self.party[j].player_role == cover:
                                break
                            j += 1
                        if (
                            j > self.max_party_member_index or
                            self.player_roles.hp[cover] == 0
                        ):
                            continue
                        if self.objects[name].player.script_on_dying != 0:
                            self.battle_delay(10, 0, True)
                            self.battle_make_scene()
                            self.blit(self.battle.scene_buf, (0, 0))
                            self.update_screen()
                            self.battle.battle_result = BattleResult.Pause
                            self.objects[name].player.script_on_dying = self.run_trigger_script(
                                self.objects[name].player.script_on_dying, w
                            )
                            self.battle.battle_result = BattleResult.OnGoing
                            self.clear_key_state()
                        return self.battle_post_action_check_end(fade)
        return self.battle_post_action_check_end(fade)

    def battle_post_action_check_end(self, fade):
        if fade:
            self.screen_bak.blit(self.battle.scene_buf, (0, 0))
            self.battle_make_scene()
            self.battle_fade_scene()
        if self.battle.summon_sprite is not None:
            self.battle_update_fighters()
            self.battle_delay(1, 0, False)
            self.battle.summon_sprite = None
            self.battle.background_color_shift = 0
            self.screen_bak.blit(self.battle.scene_buf, (0, 0))
            self.battle_make_scene()
            self.battle_fade_scene()

    def battle_enemy_perform_action(self, enemy_index):
        auto_defend = False
        mag_auto_defend = [False] * MAX_PLAYERS_IN_PARTY
        elemental_resistance = [0] * NUM_MAGIC_ELEMENTAL
        self.battle_backup_stat()
        self.battle.blow = 0
        target = self.battle_enemy_select_target_index()
        enemy = self.battle.enemies[enemy_index]
        player = self.battle.players[target]
        player_role = self.party[target].player_role
        magic = enemy.e.magic
        if (
            enemy.status[Status.Sleep] > 0 or
            enemy.status[Status.Paralyzed] > 0 or
            self.battle.hiding_time > 0
        ):
            return
        elif enemy.status[Status.Confused] > 0:
            return
        elif (
            magic != 0 and random.randint(0, 9) <
            enemy.e.magic_rate and
            enemy.status[Status.Silence] == 0
        ):
            if magic == 0xFFFF:
                return
            magic_num = self.objects[magic].magic.magic_number
            strength = enemy.e.magic_strength
            strength += (enemy.e.level + 6) * 6
            if strength < 0:
                strength = 0
            ex, ey = enemy.pos
            ex += 12
            ey += 6
            enemy.pos = ex, ey
            self.battle_delay(1, 0, False)
            ex += 4
            ey += 2
            enemy.pos = ex, ey
            self.battle_delay(1, 0, False)
            self.play_sound(enemy.e.magic_sound)
            for i in range(enemy.e.magic_frames):
                enemy.current_frame = enemy.e.idle_frames + i
                self.battle_delay(enemy.e.act_wait_frames, 0, False)
            if enemy.e.magic_frames == 0:
                self.battle_delay(1, 0, False)
            if self.magics[magic_num].fire_delay == 0:
                for i in range(enemy.e.attack_frames + 1):
                    enemy.current_frame = i - 1 + enemy.e.idle_frames + enemy.e.magic_frames
                    self.battle_delay(enemy.e.act_wait_frames, 0, False)
            if self.magics[magic_num].type != MagicType.Normal:
                target = -1
                for i in range(self.max_party_member_index + 1):
                    w = self.party[i].player_role
                    if (
                        self.player_status[w][Status.Sleep] == 0 and
                        self.player_status[w][Status.Paralyzed] == 0 and
                        self.player_status[w][Status.Confused] == 0 and
                        random.randint(0, 2) == 0 and
                        self.player_roles.hp[w] != 0
                    ):
                        mag_auto_defend[i] = True
                        self.battle.players[i].current_frame = 3
                    else:
                        mag_auto_defend[i] = False
            elif (
                    self.player_status[player_role][Status.Sleep] == 0 and
                    self.player_status[player_role][Status.Paralyzed] == 0 and
                    self.player_status[player_role][Status.Confused] == 0 and
                    random.randint(0, 2) == 0
            ):
                auto_defend = True
                player.current_frame = 3
            self.objects[magic].magic.script_on_use = self.run_trigger_script(
                self.objects[magic].magic.script_on_use, player_role
            )
            if RunResult.success:
                self.battle_show_enemy_magic_anim(
                    enemy_index, magic, target
                )
                self.objects[magic].magic.script_on_success = self.run_trigger_script(
                    self.objects[magic].magic.script_on_success, player_role
                )
            if self.magics[magic_num].base_damage > 0:
                if target == -1:
                    for i in range(self.max_party_member_index + 1):
                        w = self.party[i].player_role
                        if self.player_roles.hp[w] == 0:
                            continue
                        defense = self.get_player_defense(w)
                        for x in range(NUM_MAGIC_ELEMENTAL):
                            elemental_resistance[x] = 100 + self.get_player_elemental_resistance(w, x)
                        damage = self.calc_magic_damage(
                            strength, defense, elemental_resistance,
                            100 + self.get_player_poison_resistance(w),
                            20, magic
                        )
                        damage //= (
                                (2 if self.battle.players[i].defending else 1) *
                                (2 if self.player_status[w][Status.Protect] else 1) +
                                (1 if mag_auto_defend[i] else 0)
                        )
                        if damage > self.player_roles.hp[w]:
                            damage = self.player_roles.hp[w]
                        if not self._invincible:
                            self.player_roles.hp[w] -= damage
                        if self.player_roles.hp[w] == 0:
                            self.play_sound(self.player_roles.death_sound[w])
                else:
                    w = player_role
                    defense = self.get_player_defense(w)
                    for x in range(NUM_MAGIC_ELEMENTAL):
                        elemental_resistance[x] = 100 + self.get_player_elemental_resistance(w, x)
                    damage = self.calc_magic_damage(
                        strength, defense, elemental_resistance,
                        100 + self.get_player_poison_resistance(w),
                        20, magic
                    )
                    damage //= (
                            (2 if self.battle.players[target].defending else 1) *
                            (2 if self.player_status[w][Status.Protect] else 1) +
                            (1 if mag_auto_defend[target] else 0)
                    )
                    if damage > self.player_roles.hp[w]:
                        damage = self.player_roles.hp[w]
                    if not self._invincible:
                        self.player_roles.hp[w] -= damage
                    if self.player_roles.hp[w] == 0:
                        self.play_sound(self.player_roles.death_sound[w])
            if not self.auto_battle:
                self.battle_display_stat_change()
            for i in range(5):
                if target == -1:
                    for x in range(self.max_party_member_index + 1):
                        if (
                            self.battle.players[x].prev_hp ==
                            self.player_roles.hp[self.party[x].player_role]
                        ):
                            continue
                        self.battle.players[x].current_frame = 4
                        if i > 0:
                            self.battle.players[x].pos = (
                                pal_x(self.battle.players[x].pos) + (8 >> i),
                                pal_y(self.battle.players[x].pos) + (4 >> i)
                            )
                        self.battle.players[x].color_shift = 6 if i < 3 else 0
                else:
                    player.current_frame = 4
                    if i > 0:
                        player.pos = (
                            pal_x(player.pos) + (8 >> i),
                            pal_y(player.pos) + (4 >> i)
                        )
                    player.color_shift = 6 if i < 3 else 0
                self.battle_delay(1, 0, False)
            enemy.current_frame = 0
            enemy.pos = enemy.pos_original
            self.battle_delay(1, 0, False)
            self.battle_update_fighters()
            self.battle_post_action_check(True)
            self.battle_delay(8, 0, True)
        else:
            frame_bak = player.current_frame
            strength = enemy.e.attack_strength
            strength += (enemy.e.level + 6) * 6
            if strength < 0:
                strength = 0
            defense = self.get_player_defense(player_role)
            if player.defending:
                defense *= 2
            self.play_sound(enemy.e.attack_sound)
            cover_index = -1
            auto_defend = random.randint(0, 16) >= 10
            if (
                self.is_player_dying(player_role) or
                self.player_status[player_role][Status.Confused] > 0 or
                self.player_status[player_role][Status.Sleep] > 0 or
                self.player_status[player_role][Status.Paralyzed] > 0
            ):
                w = self.player_roles.covered_by[player_role]
                for i in range(self.max_party_member_index + 1):
                    if self.party[i].player_role == w:
                        cover_index = i
                        break
                if cover_index != -1:
                    if (
                        self.is_player_dying(cover_index) or
                        self.player_status[cover_index][Status.Confused] > 0 or
                        self.player_status[cover_index][Status.Sleep] > 0 or
                        self.player_status[cover_index][Status.Paralyzed] > 0
                    ):
                        cover_index = -1
            if cover_index == -1 and (
                    self.player_status[player_role][Status.Confused] > 0 or
                    self.player_status[player_role][Status.Sleep] > 0 or
                    self.player_status[player_role][Status.Paralyzed] > 0
            ):
                auto_defend = False
            for i in range(enemy.e.magic_frames):
                enemy.current_frame = enemy.e.idle_frames + i
                self.battle_delay(2, 0, False)
            for i in range(3 - enemy.e.magic_frames):
                x = pal_x(enemy.pos) - 2
                y = pal_y(enemy.pos) - 1
                enemy.pos = x, y
                self.battle_delay(1, 0, False)
            if not is_win95 or enemy.e.action_sound != 0:
                self.play_sound(enemy.e.action_sound)
            self.battle_delay(1, 0, False)
            ex = pal_x(player.pos) - 44
            ey = pal_y(player.pos) - 16
            sound = enemy.e.call_sound
            if cover_index != -1:
                sound = self.player_roles.cover_sound[
                    self.party[cover_index].player_role
                ]
                self.battle.players[cover_index].current_frame = 3
                x = pal_x(player.pos) - 24
                y = pal_y(player.pos) - 12
                self.battle.players[cover_index].pos = x, y
            elif auto_defend:
                player.current_frame = 3
                sound = self.player_roles.cover_sound[player_role]
            if enemy.e.attack_frames == 0:
                enemy.current_frame = enemy.e.idle_frames - 1
                enemy.pos = ex, ey
                self.battle_delay(2, 0, False)
            else:
                for i in range(enemy.e.attack_frames + 1):
                    enemy.current_frame = enemy.e.idle_frames + enemy.e.magic_frames + i - 1
                    enemy.pos = ex, ey
                    self.battle_delay(enemy.e.act_wait_frames, 0, False)
            if not auto_defend:
                player.current_frame = 4
                damage = self.calc_physical_attack_damage(
                    strength + random.randint(0, 2), defense, 2
                )
                damage += random.randint(0, 1)
                if self.player_status[player_role][Status.Protect]:
                    damage //= 2
                if self.player_roles.hp[player_role] < damage:
                    damage = self.player_roles.hp[player_role]
                if damage <= 0:
                    damage = 1
                if not self._invincible:
                    self.player_roles.hp[player_role] -= damage
                self.battle_display_stat_change()
                player.color_shift = 6
            if not is_win95 or sound != 0:
                self.play_sound(sound)
            self.battle_delay(1, 0, False)
            player.color_shift = 0
            if cover_index != -1:
                enemy.pos = (
                    pal_x(enemy.pos) - 10,
                    pal_y(enemy.pos) - 8
                )
                self.battle.players[cover_index].pos = (
                    pal_x(self.battle.players[cover_index].pos) + 4,
                    pal_y(self.battle.players[cover_index].pos) + 2
                )
            else:
                player.pos = (
                    pal_x(player.pos) + 8,
                    pal_y(player.pos) + 4
                )
            self.battle_delay(1, 0, False)
            if self.player_roles.hp[player_role] == 0:
                self.play_sound(self.player_roles.death_sound[player_role])
                frame_bak = 2
            elif self.is_player_dying(player_role):
                frame_bak = 1
            if cover_index == -1:
                player.pos = (
                    pal_x(player.pos) + 2,
                    pal_y(player.pos) + 1
                )
            self.battle_delay(3, 0, False)
            enemy.pos = enemy.pos_original
            enemy.current_frame = 0
            self.battle_delay(1, 0, False)
            player.current_frame = frame_bak
            self.battle_delay(1, 0, True)
            player.pos = player.pos_original
            self.battle_delay(4, 0, False)
            self.battle_update_fighters()
            if (
                cover_index == -1 and not auto_defend and
                enemy.e.attack_equiv_item_rate >= random.randint(1, 10)
            ):
                i = enemy.e.attack_equiv_item
                self.objects[i].item.script_on_use = self.run_trigger_script(
                    self.objects[i].item.script_on_use, player_role
                )
            self.battle_post_action_check(True)

    def battle_player_perform_action(self, player_index):
        player = self.battle.players[player_index]
        player_role = self.party[player_index].player_role
        coop_pos = [
            (208, 157), (234, 170), (260, 183)
        ]
        self.battle.moving_player_index = player_index
        self.battle.blow = 0
        orig_target = player.action.target
        self.battle_player_validate_action(player_index)
        self.battle_backup_stat()
        target = player.action.target
        enemy = self.battle.enemies[target]
        if player.action.action_type == BattleActionType.Attack:
            if target != -1:
                for t in range(2 if self.player_status[player_role][Status.DualAttack] else 1):
                    strength = self.get_player_attack_strength(player_role)
                    defense = enemy.e.defense
                    defense += (enemy.e.level + 6) * 4
                    res = enemy.e.physical_resistance
                    critical = False
                    damage = self.calc_physical_attack_damage(
                        strength, defense, res
                    )
                    damage += random.randint(1, 2)
                    if (
                        random.randint(0, 5) == 0 or
                        self.player_status[player_role][Status.Bravery] > 0
                    ):
                        damage *= 3
                        critical = True
                    if player_role == 0 and random.randint(0, 11) == 0:
                        damage *= 2
                        critical = True
                    damage = short(damage * random.triangular(1, 1.125))
                    if damage <= 0:
                        damage = 1
                    enemy.e.health -= damage
                    if t == 0:
                        player.current_frame = 7
                        self.battle_delay(4, 0, True)
                    self.battle_show_player_attack_anim(player_index, critical)
            else:
                for t in range(2 if self.player_status[player_role][Status.DualAttack] else 1):
                    division = 1
                    index = [2, 1, 0, 4, 3]
                    critical = (
                            random.randint(0, 5) == 0 or
                            self.player_status[player_role][Status.Bravery] > 0
                    )
                    if t == 0:
                        player.current_frame = 7
                        self.battle_delay(4, 0, True)
                    for i in range(MAX_ENEMIES_IN_TEAM):
                        if (
                            self.battle.enemies[index[i]].object_id == 0 or
                            index[i] > self.battle.max_enemy_index
                        ):
                            continue
                        strength = self.get_player_attack_strength(player_role)
                        defense = self.battle.enemies[index[i]].e.defense
                        defense += (self.battle.enemies[index[i]].e.level + 6) * 4
                        res = self.battle.enemies[index[i]].e.physical_resistance
                        damage = self.calc_physical_attack_damage(
                            strength, defense, res
                        )
                        damage += random.randint(1, 2)
                        if critical:
                            damage *= 3
                        damage //= division

                        damage = short(damage * random.triangular(1, 1.125))
                        if damage <= 0:
                            damage = 1
                        self.battle.enemies[index[i]].e.health -= damage
                        division += 1
                        if division > 3:
                            division = 3
                    self.battle_show_player_attack_anim(player_index, critical)
            self.battle_update_fighters()
            self.battle_make_scene()
            self.battle_delay(3, 0, True)
            self.exp.attack_exp[player_role].count += 1
            self.exp.attack_exp[player_role].count += random.randint(2, 3)
        elif player.action.action_type == BattleActionType.AttackMate:
            i = 0
            while i < self.max_party_member_index:
                if i == player_index:
                    i += 1
                    continue
                if self.player_roles.hp[self.party[i].player_role] > 0:
                    break
                i += 1
            if i <= self.max_party_member_index:
                loop = True
                while loop:
                    target = random.randint(0, self.max_party_member_index)
                    loop = target == player_index or self.player_roles.hp[self.party[target].player_role] == 0
                for j in range(2):
                    player.current_frame = 8
                    self.battle_delay(1, 0, True)
                    player.current_frame = 0
                    self.battle_delay(1, 0, True)
                self.battle_delay(2, 0, True)
                x = pal_x(self.battle.players[target].pos) + 30
                y = pal_y(self.battle.players[target].pos) + 12
                player.pos = x, y
                player.current_frame = 8
                self.battle_delay(5, 0, True)
                player.current_frame = 9
                self.play_sound(self.player_roles.weapon_sound[player_role])
                strength = self.get_player_attack_strength(player_role)
                defense = self.get_player_defense(self.party[target].player_role)
                if self.battle.players[target].defending:
                    defense *= 2
                damage = self.calc_physical_attack_damage(strength, defense, 2)
                if self.player_status[self.party[target].player_role][Status.Protect] > 0:
                    damage //= 2
                if damage <= 0:
                    damage = 1
                if damage > self.player_roles.hp[self.party[target].player_role]:
                    damage = self.player_roles.hp[self.party[target].player_role]
                self.player_roles.hp[self.party[target].player_role] -= damage
                self.battle.players[target].pos = (
                    pal_x(self.battle.players[target].pos) - 12,
                    pal_y(self.battle.players[target].pos) - 6
                )
                self.battle_delay(1, 0, True)
                self.battle.players[target].color_shift = 6
                self.battle_delay(1, 0, True)
                self.battle_display_stat_change()
                self.battle.players[target].color_shift = 0
                self.battle_delay(4, 0, True)
                self.battle_update_fighters()
                self.battle_delay(4, 0, True)
        elif player.action.action_type == BattleActionType.CoopMagic:
            obj = self.get_player_cooperative_magic(self.party[player_index].player_role)
            magic_num = self.objects[obj].magic.magic_number
            if self.magics[magic_num].type == MagicType.Summon:
                self.battle_show_player_pre_magic_anim(
                    player_index, True
                )
                self.battle_show_player_summon_magic_anim(
                    0xFFFF, obj
                )
            else:
                self.play_sound(29)
                for i in range(1, 7):
                    x = pal_x(player.pos_original) * (6 - i)
                    y = pal_y(player.pos_original) * (6 - i)
                    x += pal_x(coop_pos[0]) * i
                    y += pal_y(coop_pos[0]) * i
                    x //= 6
                    y //= 6
                    player.pos = x, y
                    t = 0
                    for j in range(self.max_party_member_index + 1):
                        if j == player_index:
                            continue
                        t += 1
                        x = pal_x(self.battle.players[j].pos_original) * (6 - i)
                        y = pal_y(self.battle.players[j].pos_original) * (6 - i)
                        x += pal_x(coop_pos[t]) * i
                        y += pal_y(coop_pos[t]) * i
                        x //= 6
                        y //= 6
                        self.battle.players[j].pos = x, y
                    self.battle_delay(1, 0, True)
                for i in range(self.max_party_member_index, -1, -1):
                    if i == player_index:
                        continue
                    self.battle.players[i].current_frame = 5
                    self.battle_delay(3, 0, True)
                player.color_shift = 6
                player.current_frame = 5
                self.battle_delay(5, 0, True)
                player.current_frame = 6
                player.color_shift = 0
                self.battle_delay(3, 0, True)
                self.battle_show_player_off_magic_anim(
                    0xFFFF, obj, target, False
                )
            for i in range(self.max_party_member_index + 1):
                if self.player_roles.hp[self.party[i].player_role] <= self.magics[magic_num].cost_mp:
                    self.player_roles.hp[self.party[i].player_role] = 1
                else:
                    self.player_roles.hp[self.party[i].player_role] -= self.magics[magic_num].cost_mp
                self.battle.players[i].state = FighterState.Wait
            self.battle_backup_stat()
            strength = 0
            for i in range(self.max_party_member_index + 1):
                strength += self.get_player_attack_strength(self.party[i].player_role)
                strength += self.get_player_magic_strength(self.party[i].player_role)
            strength //= 4
            if target == -1:
                for i in range(self.battle.max_enemy_index + 1):
                    if self.battle.enemies[i].object_id == 0:
                        continue
                    defense = self.battle.enemies[i].e.defense
                    defense += (self.battle.enemies[i].e.level + 6) * 4
                    damage = self.calc_magic_damage(
                        strength, defense,
                        self.battle.enemies[i].e.elem_resistance,
                        self.battle.enemies[i].e.poison_resistance,
                        1, obj
                    )
                    if damage <= 0:
                        damage = 1
                    self.battle.enemies[i].e.health -= damage
            else:
                defense = enemy.e.defense
                defense += (enemy.e.level + 6) * 4
                damage = self.calc_magic_damage(
                    strength, defense,
                    enemy.e.elem_resistance,
                    enemy.e.poison_resistance,
                    1, obj
                )
                if damage <= 0:
                    damage = 1
                enemy.e.health -= damage
            self.battle_display_stat_change()
            self.battle_show_post_magic_anim()
            self.battle_delay(5, 0, True)
            if self.magics[magic_num].type != MagicType.Summon:
                self.battle_post_action_check(False)
                for i in range(6, 0, -1):
                    x = pal_x(player.pos_original) * (6 - i)
                    y = pal_y(player.pos_original) * (6 - i)
                    x += pal_x(coop_pos[0]) * i
                    y += pal_y(coop_pos[0]) * i
                    x //= 6
                    y //= 6
                    player.pos = x, y
                    t = 0
                    for j in range(self.max_party_member_index + 1):
                        self.battle.players[j].current_frame = 0
                        if j == player_index:
                            continue
                        t += 1
                        x = pal_x(self.battle.players[j].pos_original) * (6 - i)
                        y = pal_y(self.battle.players[j].pos_original) * (6 - i)
                        x += pal_x(coop_pos[t]) * i
                        y += pal_y(coop_pos[t]) * i
                        x //= 6
                        y //= 6
                        self.battle.players[j].pos = x, y
                    self.battle_delay(1, 0, True)
        elif player.action.action_type == BattleActionType.Defend:
            player.defending = True
            self.exp.defense_exp[player_role].count += 2
        elif player.action.action_type == BattleActionType.Flee:
            strength = self.get_player_flee_rate(player_role)
            defense = 0
            for i in range(self.battle.max_enemy_index + 1):
                if self.battle.enemies[i].object_id == 0:
                    continue
                defense += self.battle.enemies[i].e.dexterity
                defense += (self.battle.enemies[i].e.level + 6) * 4
            if short(defense) < 0:
                defense = 0
            if strength >= random.randint(0, defense) and not self.battle.is_boss:
                self.battle_player_escape()
            else:
                player.current_frame = 0
                for i in range(3):
                    x = pal_x(player.pos) + 4
                    y = pal_y(player.pos) + 2
                    player.pos = x, y
                    self.battle_delay(1, 0, True)
                player.current_frame = 1
                self.battle_delay(8, BATTLE_LABEL_ESCAPEFAIL, True)
                self.exp.flee_exp[player_role].count += 2
        elif player.action.action_type == BattleActionType.Magic:
            obj = player.action.action_id
            magic_num = self.objects[obj].magic.magic_number
            self.battle_show_player_pre_magic_anim(
                player_index, self.magics[magic_num].type == MagicType.Summon
            )
            if not self.auto_battle:
                if self.player_roles.mp[player_role] < self.magics[magic_num].cost_mp:
                    self.player_roles.mp[player_role] = 0
                else:
                    self.player_roles.mp[player_role] -= self.magics[magic_num].cost_mp
            if self.magics[magic_num].type in {
                MagicType.ApplyToPlayer,
                MagicType.ApplyToParty,
                MagicType.Trance
            }:
                w = 0
                if player.action.target != -1:
                    w = self.party[player.action.target].player_role
                elif self.magics[magic_num].type == MagicType.Trance:
                    w = player_role
                self.objects[obj].magic.script_on_use = self.run_trigger_script(
                    self.objects[obj].magic.script_on_use, player_role
                )
                if RunResult.success:
                    self.battle_show_player_def_magic_anim(
                        player_index, obj, target
                    )
                    self.objects[obj].magic.script_on_success = self.run_trigger_script(
                        self.objects[obj].magic.script_on_success, w
                    )
                    if RunResult.success:
                        if self.magics[magic_num].type == MagicType.Trance:
                            for i in range(6):
                                player.color_shift = i * 2
                                self.battle_delay(1, 0, True)
                            self.screen_bak.blit(self.battle.scene_buf, (0, 0))
                            self.load_battle_sprites()
                            player.color_shift = 0
                            self.battle_make_scene()
                            self.battle_fade_scene()
            else:
                self.objects[obj].magic.script_on_use = self.run_trigger_script(
                    self.objects[obj].magic.script_on_use, player_role
                )
                if RunResult.success:
                    if self.magics[magic_num].type == MagicType.Summon:
                        self.battle_show_player_summon_magic_anim(
                            player_index, obj
                        )
                    else:
                        self.battle_show_player_off_magic_anim(
                            player_index, obj, target, False
                        )
                    self.objects[obj].magic.script_on_success = self.run_trigger_script(
                        self.objects[obj].magic.script_on_success, target
                    )
                    if self.magics[magic_num].base_damage > 0:
                        if target == -1:
                            strength = self.get_player_magic_strength(player_role)
                            for i in range(self.battle.max_enemy_index + 1):
                                if self.battle.enemies[i].object_id == 0:
                                    continue
                                defense = self.battle.enemies[i].e.defense
                                defense += (self.battle.enemies[i].e.level + 6) * 4
                                damage = self.calc_magic_damage(
                                    strength, defense,
                                    self.battle.enemies[i].e.elem_resistance,
                                    self.battle.enemies[i].e.poison_resistance,
                                    1, obj
                                )
                                if damage <= 0:
                                    damage = 1
                                self.battle.enemies[i].e.health -= damage
                        else:
                            strength = self.get_player_magic_strength(player_role)
                            defense = enemy.e.defense
                            defense += (enemy.e.level + 6) * 4
                            damage = self.calc_magic_damage(
                                strength, defense,
                                enemy.e.elem_resistance,
                                enemy.e.poison_resistance,
                                1, obj
                            )
                            if damage <= 0:
                                damage = 1
                            enemy.e.health -= damage
            self.battle_display_stat_change()
            self.battle_show_post_magic_anim()
            self.battle_delay(5, 0, True)
            self.battle_check_hiding_effect()
            self.exp.magic_exp[player_role].count += random.randint(2, 3)
            self.exp.magic_power_exp[player_role].count += 1
        elif player.action.action_type == BattleActionType.ThrowItem:
            obj = player.action.action_id
            for i in range(4):
                player.pos = (
                    pal_x(player.pos) - (4 - i),
                    pal_y(player.pos) - (4 - i) // 2
                )
                self.battle_delay(1, 0, True)
            self.battle_delay(2, obj, True)
            player.current_frame = 5
            self.play_sound(self.player_roles.magic_sound[player_role])
            self.battle_delay(8, obj, True)
            player.current_frame = 6
            self.battle_delay(2, obj, True)
            self.objects[obj].item.script_on_throw = self.run_trigger_script(
                self.objects[obj].item.script_on_throw, target
            )
            self.add_item_to_inventory(obj, -1)
            self.battle_display_stat_change()
            self.battle_delay(4, 0, True)
            self.battle_update_fighters()
            self.battle_delay(4, 0, True)
            self.battle_check_hiding_effect()
        elif player.action.action_type == BattleActionType.UseItem:
            obj = player.action.action_id
            self.battle_show_player_use_item_anim(
                player_index, obj, target
            )
            self.objects[obj].item.script_on_use = self.run_trigger_script(
                self.objects[obj].item.script_on_use,
                0xFFFF if target == -1 else self.party[target].player_role
            )
            if self.objects[obj].item.flags & ItemFlag.Consuming:
                self.add_item_to_inventory(obj, -1)
            self.battle_check_hiding_effect()
            self.battle_update_fighters()
            self.battle_display_stat_change()
            self.battle_delay(8, 0, True)
        elif player.action.action_type == BattleActionType.Pass:
            pass
        player.state = FighterState.Wait
        player.time_meter = 0.0
        self.battle_post_action_check(False)
        player.action.target = orig_target

    def battle_player_validate_action(self, player_index):
        player = self.battle.players[player_index]
        player_role = self.party[player_index].player_role
        object_id = player.action.action_id
        target = player.action.target
        valid = True
        to_enemy = False
        if player.action.action_type == BattleActionType.Attack:
            to_enemy = True
        elif player.action.action_type == BattleActionType.Magic:
            i = 0
            while i < MAX_PLAYER_MAGICS:
                if self.player_roles.magic[i][player_role] == object_id:
                    break
                i += 1
            if i >= MAX_PLAYER_MAGICS:
                valid = False
            w = self.objects[object_id].magic.magic_number
            if self.player_status[player_role][Status.Silence] > 0:
                valid = False
            if self.player_roles.mp[player_role] < self.magics[w].cost_mp:
                valid = False
            if self.objects[object_id].magic.flags & MagicFlag.UsableToEnemy:
                if not valid:
                    player.action.action_type = BattleActionType.Attack
                    player.action.action_id = 0
                elif self.objects[object_id].magic.flags & MagicFlag.ApplyToAll:
                    player.action.target = -1
                elif target == -1:
                    player.action.target = self.battle_select_auto_target_from(player.action.target)
                to_enemy = True
            else:
                if not valid:
                    player.action.action_type = BattleActionType.Defend
                elif self.objects[object_id].magic.flags & MagicFlag.ApplyToAll:
                    player.action.target = -1
                elif target == -1:
                    player.action.target = player_index
        elif player.action.action_type == BattleActionType.CoopMagic:
            to_enemy = True
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                if (
                    self.is_player_dying(w) or
                    self.player_status[w][Status.Silence] > 0 or
                    self.player_status[w][Status.Sleep] > 0 or
                    self.player_status[w][Status.Paralyzed] > 0 or
                    self.player_status[w][Status.Confused] > 0
                ):
                    player.action.action_type = BattleActionType.Attack
                    player.action.action_id = 0
                    break
            if player.action.action_type == BattleActionType.CoopMagic:
                if self.objects[object_id].magic.flags & MagicFlag.ApplyToAll:
                    player.action.target = -1
                elif target == -1:
                    player.action.target = self.battle_select_auto_target_from(
                        player.action.target)
        elif player.action.action_type == BattleActionType.UseItem:
            if self.get_item_amount(object_id) == 0:
                player.action.action_type = BattleActionType.Defend
            elif self.objects[object_id].item.flags & ItemFlag.ApplyToAll:
                player.action.target = -1
            elif player.action.target == -1:
                player.action.target = player_index
        elif player.action.action_type == BattleActionType.ThrowItem:
            to_enemy = True
            if self.get_item_amount(object_id) == 0:
                player.action.action_type = BattleActionType.Attack
                player.action.action_id = 0
            elif self.objects[object_id].item.flags & ItemFlag.ApplyToAll:
                player.action.target = -1
            elif player.action.target == -1:
                player.action.target = self.battle_select_auto_target_from(player.action.target)
        elif player.action.action_type == BattleActionType.AttackMate:
            if self.player_status[player_role][Status.Confused] == 0:
                to_enemy = True
                player.action.action_type = BattleActionType.Attack
                player.action.action_id = 0
            else:
                i = 0
                while i < self.max_party_member_index:
                    if (
                        i != player_index and
                        self.player_roles.hp[self.party[i].player_role] != 0
                    ):
                        break
                    i += 1
                if i > self.max_party_member_index:
                    to_enemy = True
                    player.action.action_type = BattleActionType.Attack
                    player.action.action_id = 0
        elif player.action.action_type in {
            BattleActionType.Pass,
            BattleActionType.Defend,
            BattleActionType.Flee
        }:
            pass
        if player.action.action_type == BattleActionType.Attack:
            if target == -1:
                if not self.player_can_attack_all(player_role):
                    player.action.target = self.battle_select_auto_target_from(player.action.target)
            elif self.player_can_attack_all(player_role):
                player.action.target = -1
        if to_enemy and player.action.target >= 0:
            if self.battle.enemies[player.action.target].object_id == 0:
                player.action.target = self.battle_select_auto_target_from(
                    player.action.target)
                assert player.action.target >= 0

    def battle_commit_action(self, repeat):
        player = self.battle.players[self.battle.ui.cur_player_index]
        if not repeat:
            player.action.__init__()
            player.action.action_type = self.battle.ui.action_type
            player.action.target = short(self.battle.ui.selected_index)
            if self.battle.ui.action_type == BattleActionType.Attack:
                player.action.action_id = bool(self.battle.ui.auto_attack)
            else:
                player.action.action_id = self.battle.ui.object_id
        else:
            target = player.action.target
            player.action = player.prev_action
            player.action.target = target
            if player.action.action_type == BattleActionType.Pass:
                player.action.action_type = BattleActionType.Attack
                player.action.action_id = 0
                player.action.target = -1
        action = player.action.action_type
        if action == BattleActionType.Magic:
            w = self.magics[self.objects[player.action.action_id].magic.magic_number].cost_mp
            if self.player_roles.mp[self.party[self.battle.ui.cur_player_index].player_role] < w:
                w = self.magics[self.objects[player.action.action_id].magic.magic_number].type
                if w in {MagicType.ApplyToPlayer, MagicType.ApplyToParty, MagicType.Trance}:
                    player.action.action_type = BattleActionType.Defend
                else:
                    player.action.action_type = BattleActionType.Attack
                    if player.action.target == -1:
                        player.action.target = 0
                    player.action.action_id = 0
        elif action == BattleActionType.ThrowItem:
            for w in range(MAX_INVENTORY):
                if self.inventory[w].item == player.action.action_id:
                    self.inventory[w].amount_in_use += 1
                    break
        if self.battle.ui.action_type == BattleActionType.Flee:
            self.battle.flee = True
        player.state = FighterState.Act
        self.battle.ui.state = BattleUIState.Wait

    def battle_steal_from_enemy(self, target, steal_rate):
        s = ''
        player_index = self.battle.moving_player_index
        player = self.battle.players[player_index]
        player.current_frame = 10
        offset = (target - player_index) * 8
        enemy = self.battle.enemies[target]
        x = pal_x(enemy.pos) + 64 - offset
        y = pal_y(enemy.pos) + 20 - offset // 2
        player.pos = x, y
        self.battle_delay(1, 0, True)
        for i in range(5):
            x -= i + 8
            y -= 4
            player.pos = x, y
            if i == 4:
                enemy.color_shift = 6
            self.battle_delay(1, 0, True)
        enemy.color_shift = 0
        x -= 1
        player.pos = x, y
        self.battle_delay(3, 0, True)
        player.state = FighterState.Wait
        player.time_meter = 0.0
        self.battle_update_fighters()
        self.battle_delay(1, 0, True)
        if (
            enemy.e.steal_item_num > 0 and
            (
                random.randint(0, 10) <= steal_rate or
                steal_rate == 0
            )
        ):
            if enemy.e.steal_item == 0:
                c = enemy.e.steal_item_num // random.randint(2, 3)
                enemy.e.steal_item_num -= c
                self.cash += c
                if c > 0:
                    s = '@%s @%d @%s@' % (self.words[34], c, self.words[10])
            else:
                enemy.e.steal_item_num -= 1
                self.add_item_to_inventory(enemy.e.steal_item, 1)
                s = '@'.join([self.words[34], self.words[enemy.e.steal_item], ''])
        if len(s):
            self.start_dialog(DialogPos.CenterWindow, 0, 0, False)
            self.show_dialog_text(s)

    def battle_display_stat_change(self):
        f = False
        for i in range(self.battle.max_enemy_index + 1):
            enemy = self.battle.enemies[i]
            if enemy.object_id == 0:
                continue
            if enemy.prev_hp != enemy.e.health:
                damage = enemy.e.health - enemy.prev_hp
                x = pal_x(enemy.pos) - 9
                y = max(pal_y(enemy.pos) - 115, 10)
                if damage < 0:
                    self.battle_ui_show_num(-damage, (x, y), NumColor.Blue)
                else:
                    self.battle_ui_show_num(damage, (x, y), NumColor.Yellow)
                f = True
        for i in range(self.max_party_member_index + 1):
            player_role = self.party[i].player_role
            player = self.battle.players[i]
            if player.prev_hp != self.player_roles.hp[player_role]:
                damage = self.player_roles.hp[player_role] - player.prev_hp
                x = pal_x(player.pos) - 9
                y = max(pal_y(player.pos) - 75, 10)
                if damage < 0:
                    self.battle_ui_show_num(-damage, (x, y), NumColor.Blue)
                else:
                    self.battle_ui_show_num(damage, (x, y), NumColor.Yellow)
                f = True
            if player.prev_mp != self.player_roles.mp[player_role]:
                damage = self.player_roles.mp[player_role] - player.prev_mp
                x = pal_x(player.pos) - 9
                y = max(pal_y(player.pos) - 67, 10)
                if damage > 0:
                    self.battle_ui_show_num(damage, (x, y), NumColor.Cyan)
                f = True
        return f

    def battle_update_fighters(self):
        for i in range(self.max_party_member_index + 1):
            player_role = self.party[i].player_role
            player = self.battle.players[i]
            player.pos = player.pos_original
            player.color_shift = 0
            if self.player_roles.hp[player_role] == 0:
                if self.player_status[player_role][Status.Puppet] == 0:
                    player.current_frame = 2
                else:
                    player.current_frame = 0
            else:
                if (
                    self.player_status[player_role][Status.Sleep] != 0 or
                    self.is_player_dying(player_role)
                ):
                    player.current_frame = 1
                elif player.defending and not self.battle.enemy_cleared:
                    player.current_frame = 3
                else:
                    player.current_frame = 0
        for i in range(self.battle.max_enemy_index + 1):
            enemy = self.battle.enemies[i]
            if enemy.object_id == 0:
                continue
            enemy.pos = enemy.pos_original
            enemy.color_shift = 0
            if (
                enemy.status[Status.Sleep] > 0 or
                enemy.status[Status.Paralyzed] > 0
            ):
                enemy.current_frame = 0
                continue
            enemy.e.idle_anim_speed -= 1
            if enemy.e.idle_anim_speed == 0:
                enemy.current_frame += 1
                enemy.e.idle_anim_speed = self.enemies[self.objects[enemy.object_id].enemy.enemy_id].idle_anim_speed
            if enemy.current_frame >= enemy.e.idle_frames:
                enemy.current_frame = 0

    def battle_delay(self, duration, object_id, update_gesture):
        ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
        for i in range(duration):
            if update_gesture:
                for j in range(self.battle.max_enemy_index + 1):
                    enemy = self.battle.enemies[j]
                    if (
                        enemy.object_id == 0 or
                        enemy.status[Status.Sleep] != 0 or
                        enemy.status[Status.Paralyzed] != 0
                    ):
                        continue
                    enemy.e.idle_anim_speed -= 1
                    if enemy.e.idle_anim_speed == 0:
                        enemy.current_frame += 1
                        enemy.e.idle_anim_speed = self.enemies[self.objects[enemy.object_id].enemy.enemy_id].idle_anim_speed
                    if enemy.current_frame >= enemy.e.idle_frames:
                        enemy.current_frame = 0
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            self.battle_ui_update()
            if object_id != 0:
                if object_id == BATTLE_LABEL_ESCAPEFAIL:
                    self.draw_text(
                        self.words[object_id], (130, 75), 15,
                        True, False
                    )
                elif short(object_id) < 0:
                    self.draw_text(
                        self.words[-short(object_id)], (170, 45),
                        DESCTEXT_COLOR, True, False
                    )
                else:
                    self.draw_text(
                        self.words[object_id], (210, 50), 15,
                        True, False
                    )
            self.update_screen()

    def battle_start_frame(self):
        only_puppet = True
        if not self.battle.enemy_cleared:
            self.battle_update_fighters()
        self.battle_make_scene()
        self.blit(self.battle.scene_buf, (0, 0))
        if self.battle.enemy_cleared:
            self.battle.battle_result = BattleResult.Won
            self.play_sound(0)
            return
        else:
            ended = True
            for i in range(self.max_party_member_index + 1):
                player_role = self.party[i].player_role
                if self.player_roles.hp[player_role] != 0:
                    only_puppet = ended = False
                    break
                elif self.player_status[player_role][Status.Puppet] != 0:
                    ended = False
            if ended:
                self.battle.battle_result = BattleResult.Lost
                return
        if self.battle.phase == BattlePhase.SelectAction:
            if self.battle.ui.state == BattleUIState.Wait:
                i = -1
                while True:
                    i += 1
                    if i > self.max_party_member_index:
                        break
                    player_role = self.party[i].player_role
                    player = self.battle.players[i]
                    if (
                        self.player_roles.hp[player_role] == 0 or
                        self.player_status[player_role][Status.Sleep] or
                        self.player_status[player_role][Status.Confused] or
                        self.player_status[player_role][Status.Paralyzed]
                    ):
                        continue
                    if player.state == FighterState.Wait:
                        self.battle.moving_player_index = i
                        player.state = FighterState.Com
                        self.battle_ui_player_ready(i)
                        break
                    elif player.action.action_type == BattleActionType.CoopMagic:
                        i = self.max_party_member_index + 1
                        break
                if i > self.max_party_member_index:
                    if not self.battle.repeat:
                        for i in range(self.max_party_member_index + 1):
                            self.battle.players[i].prev_action = self.battle.players[i].action
                    self.battle.repeat = False
                    self.battle.force = False
                    self.battle.flee = False
                    self.battle.prev_auto_atk = self.battle.ui.auto_attack
                    self.battle.prev_player_auto_atk = False
                    self.battle.action_queue.clear()
                    for i in range(self.battle.max_enemy_index + 1):
                        if self.battle.enemies[i].object_id == 0:
                            continue
                        action = ActionItem(
                            index=0xFFFF, dexterity=0xFFFF
                        )
                        action.is_enemy = True
                        action.index = i
                        action.dexterity = self.get_enemy_dexterity(i)
                        action.dexterity *= random.triangular(0.9, 1.1)
                        self.battle.action_queue.append(action)
                        if self.battle.enemies[i].e.dual_move * 50 + random.randint(0, 100) > 100:    
                            action = ActionItem(
                                index=0xFFFF, dexterity=0xFFFF
                            )
                            action.is_enemy = True
                            action.index = i
                            action.dexterity = self.get_enemy_dexterity(i)
                            action.dexterity *= random.triangular(0.9, 1.1)
                            self.battle.action_queue.append(action)
                    for i in range(self.max_party_member_index + 1):
                        player_role = self.party[i].player_role
                        player = self.battle.players[i]
                        action = ActionItem(
                            index=0xFFFF, dexterity=0xFFFF
                        )
                        action.is_enemy = False
                        action.index = i
                        if (
                            self.player_roles.hp[player_role] == 0 or
                            self.player_status[player_role][Status.Sleep] > 0 or
                            self.player_status[player_role][Status.Paralyzed] > 0
                        ):
                            action.dexterity = 0
                            player.action.action_type = BattleActionType.Attack
                            player.action.action_id = 0
                            player.state = FighterState.Act
                        else:
                            dexterity = self.get_player_actual_dexterity(player_role)
                            if self.player_status[player_role][Status.Confused] > 0:
                                player.action.action_type = BattleActionType.Attack
                                player.action.action_id = 0
                                player.state = FighterState.Act
                            if player.action.action_type == BattleActionType.CoopMagic:
                                dexterity *= 10
                            elif player.action.action_type == BattleActionType.Defend:
                                dexterity *= 5
                            elif player.action.action_type == BattleActionType.Magic:
                                if (self.objects[player.action.action_id].magic.flags & MagicFlag.UsableToEnemy) == 0:
                                    dexterity *= 3
                            elif player.action.action_type == BattleActionType.Flee:
                                dexterity //= 2
                            elif player.action.action_type == BattleActionType.UseItem:
                                dexterity *= 3
                            if self.is_player_dying(player_role):
                                dexterity //= 2
                            dexterity *= random.triangular(0.9, 1.1)
                            action.dexterity = dexterity
                        self.battle.action_queue.append(action)
                    self.battle.action_queue = deque(sorted(
                        self.battle.action_queue, key=attrgetter('dexterity'), reverse=True
                    ), MAX_ACTIONQUEUE_ITEMS)
                    self.battle.phase = BattlePhase.PerformAction
        else:
            if not len(self.battle.action_queue):
                for i in range(self.max_party_member_index + 1):
                    self.battle.players[i].defending = False
                self.battle_backup_stat()
                for i in range(self.max_party_member_index + 1):
                    player_role = self.party[i].player_role
                    for j in range(MAX_POISONS):
                        if self.poison_status[j][i].poison_id != 0:
                            self.poison_status[j][i].poison_script = self.run_trigger_script(
                                self.poison_status[j][i].poison_script, player_role
                            )
                    for j in range(Status.All):
                        if self.player_status[player_role][j] > 0:
                            self.player_status[player_role][j] -= 1
                for i in range(self.battle.max_enemy_index + 1):
                    for j in range(MAX_POISONS):
                        if self.battle.enemies[i].poisons[j].poison_id != 0:
                            self.battle.enemies[i].poisons[j].poison_script = self.run_trigger_script(
                                self.battle.enemies[i].poisons[j].poison_script, i
                            )
                    for j in range(Status.All):
                        if self.battle.enemies[i].status[j] > 0:
                            self.battle.enemies[i].status[j] -= 1
                self.battle_post_action_check(False)
                if self.battle_display_stat_change():
                    self.battle_delay(8, 0, True)
                if self.battle.hiding_time > 0:
                    self.battle.hiding_time -= 1
                    if self.battle.hiding_time == 0:
                        self.screen_bak.blit(self.battle.scene_buf, (0, 0))
                        self.battle_make_scene()
                        self.battle_fade_scene()
                if self.battle.hiding_time == 0:
                    for i in range(self.battle.max_enemy_index + 1):
                        if self.battle.enemies[i].object_id == 0:
                            continue
                        self.battle.enemies[i].script_on_turn_start = self.run_trigger_script(
                            self.battle.enemies[i].script_on_turn_start, i
                        )
                for i in range(MAX_INVENTORY):
                    self.inventory[i].amount_in_use = 0
                self.battle.phase = BattlePhase.SelectAction
            else:
                action = self.battle.action_queue.popleft()
                i = action.index
                if action.is_enemy:
                    if (
                        self.battle.hiding_time == 0 and not only_puppet and
                        self.battle.enemies[i].object_id != 0
                    ):
                        self.battle.enemies[i].script_on_ready = self.run_trigger_script(
                            self.battle.enemies[i].script_on_ready, i
                        )
                        self.battle.enemy_moving = True
                        self.battle_enemy_perform_action(i)
                        self.battle.enemy_moving = False
                elif self.battle.players[i].state == FighterState.Act:
                    player_role = self.party[i].player_role
                    if self.player_roles.hp[player_role] == 0:
                        if self.player_status[player_role][Status.Puppet] == 0:
                            self.battle.players[i].action.action_type = BattleActionType.Pass
                    elif (
                            self.player_status[player_role][Status.Sleep] > 0 or
                            self.player_status[player_role][Status.Paralyzed] > 0
                    ):
                        self.battle.players[i].action.action_type = BattleActionType.Pass
                    elif self.player_status[player_role][Status.Confused] > 0:
                        self.battle.players[i].action.action_type = BattleActionType.Pass if self.is_player_dying(player_role) else BattleActionType.AttackMate
                    elif (
                            self.battle.players[i].action.action_type == BattleActionType.Attack and
                            self.battle.players[i].action.action_id != 0
                    ):
                        self.battle.prev_player_auto_atk = True
                    elif self.battle.prev_player_auto_atk:
                        self.battle.ui.cur_player_index = 1
                        self.battle.ui.selected_index = self.battle.players[i].action.target
                        self.battle.ui.action_type = BattleActionType.Attack
                        self.battle_commit_action(False)
                    self.battle.moving_player_index = i
                    self.battle_player_perform_action(i)
        if (
            self.battle.ui.menu_state == BattleMenuState.Main and
            self.battle.ui.state == BattleUIState.SelectMove
        ):
            if self.input_state.key_press & Key.Repeat:
                self.battle.repeat = True
                self.battle.ui.auto_attack = self.battle.prev_auto_atk
            elif self.input_state.key_press & Key.Force:
                self.battle.force = True
        if self.battle.repeat:
            self.input_state.key_press = Key.Repeat
        elif self.battle.force:
            self.input_state.key_press = Key.Force
        elif self.battle.flee:
            self.input_state.key_press = Key.Flee
        self.battle_ui_update()

    def battle_enemy_select_target_index(self):
        i = random.randint(0, self.max_party_member_index)
        while self.player_roles.hp[self.party[i].player_role] == 0:
            i = random.randint(0, self.max_party_member_index)
        return i

    def battle_check_hiding_effect(self):
        if self.battle.hiding_time < 0:
            self.battle.hiding_time = -self.battle.hiding_time
            self.screen_bak.blit(self.battle.scene_buf, (0, 0))
            self.battle_make_scene()
            self.battle_fade_scene()

    def battle_backup_stat(self):
        for i in range(self.battle.max_enemy_index + 1):
            if self.battle.enemies[i].object_id == 0:
                continue
            self.battle.enemies[i].prev_hp = self.battle.enemies[i].e.health
        for i in range(self.max_party_member_index + 1):
            player_role = self.party[i].player_role
            self.battle.players[i].prev_hp = self.player_roles.hp[player_role]
            self.battle.players[i].prev_mp = self.player_roles.mp[player_role]

    def battle_player_check_ready(self):
        fl_max = 0.0
        i_max = 0
        for i in range(self.max_party_member_index + 1):
            if (
                self.battle.players[i].state == FighterState.Com or (
                    self.battle.players[i].state == FighterState.Act and
                    self.battle.players[i].action.action_type == BattleActionType.CoopMagic
                )
            ):
                fl_max = 0.0
                break
            elif self.battle.players[i].state == FighterState.Wait:
                if self.battle.players[i].time_meter > fl_max:
                    i_max = i
                    fl_max = self.battle.players[i].time_meter
        if fl_max >= 100.0:
            self.battle.players[i_max].state = FighterState.Com
            self.battle.players[i_max].defending = False

    def battle_select_auto_target_from(self, begin):
        i = self.battle.ui.prev_enemy_target
        if (
            0 <= i <= self.battle.max_enemy_index and
            self.battle.enemies[i].object_id != 0 and
            self.battle.enemies[i].e.health > 0
        ):
            return i
        i = max(begin, 0)
        for _ in range(MAX_ENEMIES_IN_TEAM):
            if (
                self.battle.enemies[i].object_id != 0 and
                self.battle.enemies[i].e.health > 0
            ):
                return i
            i = (i + 1) % MAX_ENEMIES_IN_TEAM
        return -1

    battle_select_auto_target = partialmethod(battle_select_auto_target_from, 0)

    def is_player_dying(self, player_role):
        return self.player_roles.hp[player_role] < min(
            100, self.player_roles.max_hp[player_role] // 5
        )

    def get_enemy_dexterity(self, enemy_index):
        assert self.battle.enemies[enemy_index].object_id != 0
        s = (self.battle.enemies[enemy_index].e.level + 6) * 3
        s += self.battle.enemies[enemy_index].e.dexterity
        return s

    def get_player_actual_dexterity(self, player_role):
        dexterity = self.get_player_dexterity(player_role)
        if self.player_status[player_role][Status.Haste] != 0:
            dexterity *= 3
        if self.is_player_dying(player_role):
            dexterity //= 2
        if dexterity > 999:
            dexterity = 999
        return dexterity

    def calc_base_damage(self, attack_strength, defense):
        if attack_strength > defense:
            damage = short(attack_strength * 2 - defense * 1.6 + 0.5)
        elif attack_strength > defense * 0.6:
            damage = short(attack_strength - defense * 0.6 + 0.5)
        else:
            damage = 0
        return damage

    def calc_physical_attack_damage(self, attack_strength, defense, attack_resistance):
        damage = self.calc_base_damage(attack_strength, defense)
        if attack_resistance != 0:
            damage //= attack_resistance
        return damage

    def calc_magic_damage(
        self,
        magic_strength,
        defense,
        elemental_resistance,
        poison_resistance,
        resistance_multiplier,
        magic_id
    ):
        magic_id = self.objects[magic_id].magic.magic_number
        magic_strength *= random.triangular(10, 11)
        magic_strength //= 10
        damage = self.calc_base_damage(magic_strength, defense)
        damage //= 4
        damage += self.magics[magic_id].base_damage
        if self.magics[magic_id].elemental != 0:
            elem = self.magics[magic_id].elemental
            if elem > NUM_MAGIC_ELEMENTAL:
                damage *= 10 - poison_resistance / resistance_multiplier
            elif elem == 0:
                damage *= 5
            else:
                damage *= 10 - elemental_resistance[elem - 1] / resistance_multiplier
            damage = int(round(damage / 5))
            if elem <= NUM_MAGIC_ELEMENTAL:
                damage *= 10 + self.battle_fields[self.num_battle_field].magic_effect[elem - 1]
                damage //= 10
        return damage

    def battle_simulate_magic(self, target, magic_object_id, base_damage):
        magic = self.objects[magic_object_id].magic
        if magic.flags & MagicFlag.ApplyToAll:
            target = -1
        elif target == -1:
            target = self.battle_select_auto_target_from(target)
        self.battle_show_player_off_magic_anim(0xFFFF, magic_object_id, target, False)
        if self.magics[magic.magic_number].base_damage > 0 or base_damage > 0:
            if target == -1:
                targets = range(self.battle.max_enemy_index + 1)
            else:
                targets = [target]
            for i in targets:
                enemy = self.battle.enemies[i]
                if enemy.object_id == 0:
                    continue
                defense = enemy.e.defense
                defense += (enemy.e.level + 6) * 4
                if defense < 0:
                    defense = 0
                damage = self.calc_magic_damage(
                    base_damage, defense,
                    enemy.e.elem_resistance,
                    enemy.e.poison_resistance,
                    1, magic_object_id
                )
                if damage < 0:
                    damage = 0
                enemy.e.health -= damage

    def battle_show_post_magic_anim(self):
        dist = 8
        enemy_pos_bak = [
            self.battle.enemies[i].pos
            for i in range(MAX_ENEMIES_IN_TEAM)
        ]
        for i in range(3):
            for j in range(self.battle.max_enemy_index + 1):
                if self.battle.enemies[j].e.health == self.battle.enemies[j].prev_hp:
                    continue
                x, y = self.battle.enemies[j].pos
                x -= dist
                y -= dist // 2
                self.battle.enemies[j].pos = x, y
                self.battle.enemies[j].color_shift = 6 if i == 1 else 0
            self.battle_delay(1, 0, True)
            dist //= -2
        for i in range(MAX_ENEMIES_IN_TEAM):
            self.battle.enemies[i].pos = enemy_pos_bak[i]
        self.battle_delay(1, 0, True)

    def battle_show_enemy_magic_anim(self, enemy_index, object_id, target):
        ticks = pg.time.get_ticks()
        magic_num = self.objects[object_id].magic.magic_number
        effect_num = self.magics[magic_num].effect
        if effect_num > len(self.fire.mkf):
            return
        sprite_effect = self.fire[effect_num]
        n = len(sprite_effect)
        l = n - self.magics[magic_num].fire_delay
        l *= self.magics[magic_num].effect_times
        l += n
        l += self.magics[magic_num].shake
        wave = self.screen_wave
        self.screen_wave = self.magics[magic_num].wave
        for i in range(l):
            blow = random.randint(0, self.battle.blow) if self.battle.blow > 0 else random.randint(self.battle.blow, 0)
            for k in range(self.max_party_member_index + 1):
                x = pal_x(self.battle.players[k].pos) + blow
                y = pal_y(self.battle.players[k].pos) + blow // 2
                self.battle.players[k].pos = x, y
            if l - i > self.magics[magic_num].shake:
                if i < n:
                    k = i
                else:
                    k = i - self.magics[magic_num].fire_delay
                    k %= n - self.magics[magic_num].fire_delay
                    k += self.magics[magic_num].fire_delay
                b = sprite_effect[k]
                if i == 0 if is_win95 else self.magics[magic_num].fire_delay:
                    self.play_sound(self.magics[magic_num].sound)
                if (
                    self.magics[magic_num].fire_delay > 0 and
                    self.magics[magic_num].fire_delay <= i <
                    self.magics[magic_num].fire_delay +
                    self.battle.enemies[enemy_index].e.attack_frames
                ):
                    self.battle.enemies[enemy_index].current_frame = (
                            i - self.magics[magic_num].fire_delay +
                            self.battle.enemies[enemy_index].e.idle_frames +
                            self.battle.enemies[enemy_index].e.magic_frames
                    )
            else:
                self.shake_time = i
                self.shake_level = 3
                b = sprite_effect[(i - self.magics[magic_num].shake - 1) % n]
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + (self.magics[magic_num].speed + 5) * 10
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            if self.magics[magic_num].type == MagicType.Normal:
                assert target != -1
                x, y = self.battle.players[target].pos
                x += self.magics[magic_num].x_offset
                y += self.magics[magic_num].y_offset
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                if (
                    i == l - 1 and self.screen_wave < 9 and
                    self.magics[magic_num].keep_effect == 0xFFFF
                ):
                    b.blit_to(self.battle.background, (
                        x - b.width // 2, y - b.height
                    ))
            elif self.magics[magic_num].type == MagicType.AttackAll:
                effectpos = [(180, 180), (234, 170), (270, 146)]
                assert target == -1
                for k in range(3):
                    x, y = effectpos[k]
                    x += self.magics[magic_num].x_offset
                    y += self.magics[magic_num].y_offset
                    b.blit_to(self.screen, (
                        x - b.width // 2, y - b.height
                    ))
                    if (
                        i == l - 1 and self.screen_wave < 9 and
                        self.magics[magic_num].keep_effect == 0xFFFF
                    ):
                        b.blit_to(self.battle.background, (
                            x - b.width // 2, y - b.height
                        ))
            elif self.magics[magic_num].type in {MagicType.AttackWhole, MagicType.AttackField}:
                assert target == -1
                if self.magics[magic_num].type == MagicType.AttackWhole:
                    x, y = 240, 150
                else:
                    x, y = 160, 200
                x += self.magics[magic_num].x_offset
                y += self.magics[magic_num].y_offset
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                if (
                    i == l - 1 and self.screen_wave < 9 and
                    self.magics[magic_num].keep_effect == 0xFFFF
                ):
                    b.blit_to(self.battle.background, (
                        x - b.width // 2, y - b.height
                    ))
            else:
                assert False
            self.battle_ui_update()
            self.update_screen()
        self.screen_wave = wave
        self.shake_time = self.shake_level = 0
        for i in range(self.max_party_member_index + 1):
            self.battle.players[i].pos = self.battle.players[i].pos_original

    def battle_show_player_attack_anim(self, player_index, critical):
        player_role = self.party[player_index].player_role
        player = self.battle.players[player_index]
        enemy_x = enemy_y = enemy_h = dist = 0
        target = player.action.target
        if target != -1:
            enemy_x, enemy_y = self.battle.enemies[target].pos
            enemy_h = self.battle.enemies[target].sprite[
                self.battle.enemies[target].current_frame
            ].height
            if target >= 3:
                dist = (target - player_index) * 8
        else:
            enemy_x, enemy_y = 150, 100
        index = self.battle_effect_index[self.get_player_battle_sprite(player_role)][1]
        index *= 3
        if self.player_roles.hp[player_role] > 0:
            if not critical:
                self.play_sound(self.player_roles.attack_sound[player_role])
            else:
                self.play_sound(self.player_roles.critical_sound[player_role])
        x = enemy_x - dist + 64
        y = enemy_y + dist + 20
        player.current_frame = 8
        player.pos = x, y
        self.battle_delay(2, 0, True)
        x -= 10
        y -= 2
        player.pos = x, y
        self.battle_delay(1, 0, True)
        player.current_frame = 9
        x -= 16
        y -= 4
        self.play_sound(self.player_roles.weapon_sound[player_role])
        x = enemy_x
        y = enemy_y - enemy_h // 3 + 10
        ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
        for i in range(3):
            b = self.battle.effect_sprite[index]
            index += 1
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
            for j in range(self.battle.max_enemy_index + 1):
                if (
                    self.battle.enemies[j].object_id == 0 or
                    self.battle.enemies[j].status[Status.Sleep] > 0 or
                    self.battle.enemies[j].status[Status.Paralyzed] > 0
                ):
                    continue
                self.battle.enemies[j].e.idle_anim_speed -= 1
                if self.battle.enemies[j].e.idle_anim_speed == 0:
                    self.battle.enemies[j].current_frame += 1
                    self.battle.enemies[j].e.idle_anim_speed = (
                        self.enemies[
                            self.objects[self.battle.enemies[j].object_id].enemy.enemy_id
                        ].idle_anim_speed
                    )
                if self.battle.enemies[j].current_frame >= self.battle.enemies[j].e.idle_frames:
                    self.battle.enemies[j].current_frame = 0
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            b.blit_to(self.screen, (
                x - b.width // 2, y - b.height
            ))
            x -= 16
            y += 16
            self.battle_ui_update()
            if i == 0:
                if target == -1:
                    for j in range(self.battle.max_enemy_index + 1):
                        self.battle.enemies[j].color_shift = 6
                else:
                    self.battle.enemies[target].color_shift = 6
                self.battle_display_stat_change()
                self.battle_backup_stat()
            self.update_screen()
            if i == 1:
                player.pos = (
                    pal_x(player.pos) + 2,
                    pal_y(player.pos) + 1
                )
        dist = 8
        for i in range(self.battle.max_enemy_index + 1):
            self.battle.enemies[i].color_shift = 0
        if target == -1:
            for i in range(3):
                for j in range(self.battle.max_enemy_index + 1):
                    x, y = self.battle.enemies[j].pos
                    x -= dist
                    y -= dist // 2
                    self.battle.enemies[j].pos = x, y
                self.battle_delay(1, 0, True)
                dist //= -2
        else:
            x, y = self.battle.enemies[target].pos
            for i in range(3):
                x -= dist
                dist //= -2
                y += dist
                self.battle.enemies[target].pos = x, y
                self.battle_delay(1, 0, True)

    def battle_show_player_def_magic_anim(self, player_index, object_id, target):
        ticks = pg.time.get_ticks()
        magic_num = self.objects[object_id].magic.magic_number
        effect_num = self.magics[magic_num].effect
        if effect_num > len(self.fire.mkf):
            return
        sprite_effect = self.fire[effect_num]
        n = len(sprite_effect)
        player = self.battle.players[player_index]
        player.current_frame = 6
        self.battle_delay(1, 0, True)
        for i in range(n):
            b = sprite_effect[i]
            if i == (0 if is_win95 else self.magics[magic_num].fire_delay):
                self.play_sound(self.magics[magic_num].sound)
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + (self.magics[magic_num].speed + 5) * 10
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            if self.magics[magic_num].type == MagicType.ApplyToParty:
                assert target == -1
                for l in range(self.max_party_member_index + 1):
                    x, y = self.battle.players[l].pos
                    x += self.magics[magic_num].x_offset
                    y += self.magics[magic_num].y_offset
                    b.blit_to(self.screen, (
                        x - b.width // 2, y - b.height
                    ))
            elif self.magics[magic_num].type == MagicType.ApplyToPlayer:
                assert target != -1
                x, y = self.battle.players[target].pos
                x += self.magics[magic_num].x_offset
                y += self.magics[magic_num].y_offset
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                if target > 0 and self.battle.hiding_time == 0:
                    if self.player_status[self.party[target - 1].player_role][Status.Confused] == 0:
                        p = self.battle.players[target - 1].sprite[
                            self.battle.players[target - 1].current_frame
                        ]
                        x, y = self.battle.players[target - 1].pos
                        p.blit_to(self.screen, (
                            x - p.width // 2, y - p.height
                        ))
            else:
                assert False
            self.battle_ui_update()
            self.update_screen()
        for i in chain(range(6), range(6, -1, -1)):
            if self.magics[magic_num].type == MagicType.ApplyToParty:
                for j in range(self.max_party_member_index + 1):
                    self.battle.players[j].color_shift = i
            else:
                self.battle.players[target].color_shift = i
            self.battle_delay(1, 0, True)

    def battle_show_player_off_magic_anim(self, player_index, object_id, target, summon):
        ticks = pg.time.get_ticks()
        magic_num = self.objects[object_id].magic.magic_number
        effect_num = self.magics[magic_num].effect
        if effect_num > len(self.fire.mkf):
            return
        sprite_effect = self.fire[effect_num]
        n = len(sprite_effect)
        if is_win95 and player_index != 0xFFFF:
            self.battle.players[player_index].current_frame = 6
        self.battle_delay(1, 0, True)
        l = n - self.magics[magic_num].fire_delay
        l *= self.magics[magic_num].effect_times
        l += n
        l += self.magics[magic_num].shake
        wave = self.screen_wave
        self.screen_wave = self.magics[magic_num].wave
        if is_win95 and not summon and self.magics[magic_num].sound != 0:
            self.play_sound(self.magics[magic_num].sound)
        for i in range(l):
            if not is_win95 and i == self.magics[magic_num].fire_delay and player_index != 0xFFFF:
                self.battle.players[player_index].current_frame = 6
            blow = random.randint(0, self.battle.blow) if self.battle.blow > 0 else random.randint(self.battle.blow, 0)
            for k in range(self.battle.max_enemy_index + 1):
                if self.battle.enemies[k].object_id == 0:
                    continue
                x = pal_x(self.battle.enemies[k].pos) + blow
                y = pal_y(self.battle.enemies[k].pos) + blow // 2
                self.battle.enemies[k].pos = x, y
            if l - i > self.magics[magic_num].shake:
                if i < n:
                    k = i
                else:
                    k = i - self.magics[magic_num].fire_delay
                    k %= n - self.magics[magic_num].fire_delay
                    k += self.magics[magic_num].fire_delay
                b = sprite_effect[k]
            else:
                self.shake_time = i
                self.shake_level = 3
                b = sprite_effect[(l - self.magics[magic_num].shake - 1) % n]
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + (self.magics[magic_num].speed + 5) * 10
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            if self.magics[magic_num].type == MagicType.Normal:
                assert target != -1
                x, y = self.battle.enemies[target].pos
                x += self.magics[magic_num].x_offset
                y += self.magics[magic_num].y_offset
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                if (
                    i == l - 1 and self.screen_wave < 9 and
                    self.magics[magic_num].keep_effect == 0xFFFF
                ):
                    b.blit_to(self.battle.background, (
                        x - b.width // 2, y - b.height
                    ))
            elif self.magics[magic_num].type == MagicType.AttackAll:
                effectpos = [(70, 140), (100, 110), (160, 100)]
                assert target == -1
                for k in range(3):
                    x, y = effectpos[k]
                    x += self.magics[magic_num].x_offset
                    y += self.magics[magic_num].y_offset
                    b.blit_to(self.screen, (
                        x - b.width // 2, y - b.height
                    ))
                    if (
                        i == l - 1 and self.screen_wave < 9 and
                        self.magics[magic_num].keep_effect == 0xFFFF
                    ):
                        b.blit_to(self.battle.background, (
                            x - b.width // 2, y - b.height
                        ))
            elif self.magics[magic_num].type in {MagicType.AttackWhole, MagicType.AttackField}:
                assert target == -1
                if self.magics[magic_num].type == MagicType.AttackWhole:
                    x, y = 120, 100
                else:
                    x, y = 160, 200
                x += self.magics[magic_num].x_offset
                y += self.magics[magic_num].y_offset
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                if (
                    i == l - 1 and self.screen_wave < 9 and
                    self.magics[magic_num].keep_effect == 0xFFFF
                ):
                    b.blit_to(self.battle.background, (
                        x - b.width // 2, y - b.height
                    ))
            else:
                assert False
            self.battle_ui_update()
            self.update_screen()
        self.screen_wave = wave
        self.shake_time = self.shake_level = 0
        for i in range(self.battle.max_enemy_index + 1):
            self.battle.enemies[i].pos = self.battle.enemies[i].pos_original

    def battle_show_player_pre_magic_anim(self, player_index, summon):
        ticks = pg.time.get_ticks()
        player = self.battle.players[player_index]
        player_role = self.party[player_index].player_role
        for i in range(4):
            player.pos = (
                pal_x(player.pos) - (4 - i),
                pal_y(player.pos) - (4 - i) // 2,
            )
            self.battle_delay(1, 0, True)
        self.battle_delay(2, 0, True)
        player.current_frame = 5
        if not is_win95:
            self.play_sound(self.player_roles.magic_sound[player_role])
        if not summon:
            x, y = player.pos
            index = self.battle_effect_index[self.get_player_battle_sprite(player_role)][0]
            index *= 10
            index += 15
            if is_win95:
                self.play_sound(self.player_roles.magic_sound[player_role])
            for i in range(10):
                b = self.battle.effect_sprite[index]
                index += 1
                self.delay_until(ticks)
                ticks = pg.time.get_ticks() + BATTLE_FRAME_TIME
                for j in range(self.battle.max_enemy_index + 1):
                    if (
                        self.battle.enemies[j].object_id == 0 or
                        self.battle.enemies[j].status[Status.Sleep] != 0 or
                        self.battle.enemies[j].status[Status.Paralyzed] != 0
                    ):
                        continue
                    self.battle.enemies[j].e.idle_anim_speed -= 1
                    if self.battle.enemies[j].e.idle_anim_speed == 0:
                        self.battle.enemies[j].current_frame += 1
                        self.battle.enemies[j].e.idle_anim_speed = (
                            self.enemies[
                                self.objects[self.battle.enemies[j].object_id].enemy.enemy_id
                            ].idle_anim_speed
                        )
                    if self.battle.enemies[j].current_frame >= self.battle.enemies[j].e.idle_frames:
                        self.battle.enemies[j].current_frame = 0
                self.battle_make_scene()
                self.blit(self.battle.scene_buf, (0, 0))
                b.blit_to(self.screen, (
                    x - b.width // 2, y - b.height
                ))
                self.battle_ui_update()
                self.update_screen()
        self.battle_delay(1, 0, True)

    def battle_show_player_summon_magic_anim(self, player_index, object_id):
        magic_num = self.objects[object_id].magic.magic_number
        effect_magic_id = 0
        ticks = pg.time.get_ticks()
        while effect_magic_id < MAX_OBJECTS:
            if self.objects[effect_magic_id].magic.magic_number == self.magics[magic_num].effect:
                break
            effect_magic_id += 1
        assert effect_magic_id < MAX_OBJECTS
        if is_win95:
            self.play_sound(self.magics[magic_num].sound)
        for i in range(1, 11):
            for j in range(self.max_party_member_index + 1):
                self.battle.players[j].color_shift = i
            self.battle_delay(1, object_id, True)
        self.screen_bak.blit(self.battle.scene_buf, (0, 0))
        j = self.magics[magic_num].summon_effect + 10
        self.battle.summon_sprite = self.f[j]
        self.battle.summon_frame = 0
        self.battle.pos_summon = (
            230 + self.magics[magic_num].x_offset,
            155 + self.magics[magic_num].y_offset
        )
        self.battle.background_color_shift = self.magics[magic_num].effect_times
        self.battle_make_scene()
        self.battle_fade_scene()
        while self.battle.summon_frame < len(self.battle.summon_sprite) - 1:
            self.delay_until(ticks)
            ticks = pg.time.get_ticks() + (self.magics[magic_num].speed + 5) * 10
            self.battle_make_scene()
            self.blit(self.battle.scene_buf, (0, 0))
            self.battle_ui_update()
            self.update_screen()
            self.battle.summon_frame += 1
        self.battle_show_player_off_magic_anim(
            0xFFFF, effect_magic_id, -1, True
        )

    def battle_show_player_use_item_anim(self, player_index, object_id, target):
        self.battle_delay(4, 0, True)
        self.battle.players[player_index].pos = (
            pal_x(self.battle.players[player_index].pos) - 15,
            pal_y(self.battle.players[player_index].pos) - 7
        )
        self.battle.players[player_index].current_frame = 5
        self.play_sound(28)
        for i in chain(range(7), range(5, -1, -1)):
            if target == -1:
                for j in range(self.max_party_member_index + 1):
                    self.battle.players[j].color_shift = i
            else:
                self.battle.players[target].color_shift = i
            self.battle_delay(1, object_id, True)
