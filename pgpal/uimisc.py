#! /usr/bin/env python
# -*- coding: utf8 -*-
from functools import partial
import random
import attr
from pgpal import config
from pgpal.compat import pg, range, partialmethod
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.mkfext import Ball, Data, FBP, MGO, RGM, SubPlace
from pgpal.utils import (
    pal_x, pal_y, pal_xy_offset, static_vars, short, byte, RunResult
)


@attr.s(slots=True)
class MenuItem(object):
    value = attr.ib(factory=int)
    label = attr.ib(factory=str)
    enabled = attr.ib(factory=bool)
    pos = attr.ib(default=(0, 0))


@attr.s(slots=True)
class MagicItem(object):
    magic = attr.ib(factory=int)
    mp = attr.ib(factory=int)
    enabled = attr.ib(factory=bool)


@attr.s
class Box(object):
    rect = attr.ib(default=(0, 0, 0, 0))
    saved_area = attr.ib(default=None)


class UIMixin(object):
    def __init__(self):
        self.fbp = FBP()
        self.mgo = MGO()
        self.rgm = RGM()
        self.sprite_ui = SubPlace(Data().read(CHUNKNUM_SPRITEUI))

    def show_player_status(self):
        labels0 = [STATUS_LABEL_EXP, STATUS_LABEL_LEVEL, STATUS_LABEL_HP,
                   STATUS_LABEL_MP]
        labels = [
            STATUS_LABEL_ATTACKPOWER, STATUS_LABEL_MAGICPOWER, STATUS_LABEL_RESISTANCE,
            STATUS_LABEL_DEXTERITY, STATUS_LABEL_FLEERATE
        ]
        buf_background = partial(self.fbp.render, STATUS_BACKGROUND_FBPNUM)
        current = 0

        while 0 <= current <= self.max_party_member_index:
            player_role = self.party[current].player_role
            buf_background(self.screen)
            head_icon = self.rgm[self.player_roles.avatar[player_role]]
            if head_icon is not None:
                head_icon.blit_to(self.screen, self.screen_layout.role_image)
            for i in range(MAX_PLAYER_EQUIPMENTS):
                w = self.player_roles.equipment[i][player_role]
                if w == 0:
                    continue
                item_icon = self.ball[self.objects[w].item.bitmap]
                if item_icon is not None:
                    item_icon.blit_to(
                        self.screen,
                        pal_xy_offset(self.screen_layout.role_equip_image_boxes[i], 1, 1)
                    )
                offset = self.word_width(w) * 16
                if pal_x(self.screen_layout.role_equip_names[i]) + offset > 320:
                    offset = 320 - pal_x(self.screen_layout.role_equip_names[i]) - offset
                else:
                    offset = 0
                self.draw_text(
                    self.words[w],
                    pal_xy_offset(self.screen_layout.role_equip_names[i], offset, 0),
                    STATUS_COLOR_EQUIPMENT, False, False
                )
            for i, index in enumerate(labels0):
                self.draw_text(
                    self.words[index],
                    getattr(
                        self.screen_layout,
                        self.screen_layout.__slots__[10 + i]
                    ),
                    MENUITEM_COLOR, False, False
                )
            for i, index in enumerate(labels):
                self.draw_text(
                    self.words[index],
                    self.screen_layout.role_status_labels[i],
                    MENUITEM_COLOR, False, False
                )
            self.draw_text(
                self.words[self.player_roles.name[player_role]],
                self.screen_layout.role_name, MENUITEM_COLOR_CONFIRMED,
                True, False
            )
            if self.screen_layout.role_exp_slash != (0, 0):
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen,
                    self.screen_layout.role_exp_slash
                )
            if self.screen_layout.role_hp_slash != (0, 0):
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen,
                    self.screen_layout.role_hp_slash
                )
            if self.screen_layout.role_mp_slash != (0, 0):
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen,
                    self.screen_layout.role_mp_slash
                )
            self.draw_number(
                self.exp.primary_exp[player_role].exp, 5,
                self.screen_layout.role_curr_exp,
                NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.level_up_exp[self.player_roles.level[player_role]], 5,
                self.screen_layout.role_next_exp,
                NumColor.Cyan, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.level[player_role], 2,
                self.screen_layout.role_level,
                NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.hp[player_role], 4,
                self.screen_layout.role_cur_hp,
                NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.max_hp[player_role], 4,
                self.screen_layout.role_max_hp,
                NumColor.Blue, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.mp[player_role], 4,
                self.screen_layout.role_cur_mp,
                NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.max_mp[player_role], 4,
                self.screen_layout.role_max_mp,
                NumColor.Blue, NumAlign.Right
            )

            for i, name in enumerate([
                'attack_strength',
                'magic_strength',
                'defense',
                'dexterity',
                'flee_rate'
            ]):
                self.draw_number(
                    self.get_player_stat(player_role, name), 4,
                    self.screen_layout.role_status_values[i],
                    NumColor.Yellow, NumAlign.Right
                )

            j = 0
            for i in range(MAX_POISONS):
                w = self.poison_status[i][current].poison_id
                if w != 0 and self.objects[w].poison.poison_level <= 3:
                    self.draw_text(
                        self.words[w], self.screen_layout.role_poison_names[j],
                        self.objects[w].poison.color + 10, True, False
                    )
                    j += 1
            self.update_screen()
            self.clear_key_state()
            while True:
                self.delay(0.001)
                if self.input_state.key_press & Key.Menu:
                    current = -1
                    break
                elif self.input_state.key_press & (Key.Left | Key.Up):
                    current -= 1
                    break
                elif self.input_state.key_press & (Key.Right | Key.Down | Key.Search):
                    current += 1
                    break

    def quit(self):
        result = self.confirm_menu()
        if result:
            config.write()
            self.play_music(0, False, 2)
            self.fadeout(2)
            self.shutdown()

    def create_box_internal(self, rect):
        return Box(
            rect=rect.copy(),
            saved_area=self.screen.subsurface(rect).copy()
        )

    def delete_box(self, box):
        if box is not None:
            self.blit(box.saved_area, box.rect)

    def create_box_with_shadow(
        self, pos, row_num, column_num, style, save_screen, shadow_offset
    ):
        box = None
        border_bitmaps = [
            [
                i * 3 + j + style * 9
                for j in range(3)
            ]
            for i in range(3)
        ]
        rect = pg.Rect(pos, (0, 0))
        for i in range(3):
            if i == 1:
                rect.w += self.sprite_ui[border_bitmaps[0][i]].width * column_num
                rect.h += self.sprite_ui[border_bitmaps[i][0]].height * row_num
            else:
                rect.w += self.sprite_ui[border_bitmaps[0][i]].width
                rect.h += self.sprite_ui[border_bitmaps[i][0]].height
        rect.w += shadow_offset
        rect.h += shadow_offset
        if save_screen:
            box = self.create_box_internal(rect)
        row_num += 2
        column_num += 2
        for i in range(row_num):
            x = rect.x
            m = 0 if i == 0 else (2 if i == row_num - 1 else 1)
            for j in range(column_num):
                n = 0 if j == 0 else (2 if j == column_num - 1 else 1)
                bitmap = self.sprite_ui[border_bitmaps[m][n]]
                if shadow_offset > 0:
                    bitmap.blit_to_with_shadow(
                        self.screen, (
                            x + shadow_offset, rect.y + shadow_offset
                        ), True
                    )
                bitmap.blit_to(self.screen, (x, rect.y))
                x += bitmap.width
            rect.y += self.sprite_ui[border_bitmaps[m][0]].height
        return box

    def one_line_box_with_shadow(self, pos, length, save_screen, shadow_offset):
        box = None
        bitmap_left, bitmap_mid, bitmap_right = (
            self.sprite_ui[i]
            for i in range(44, 47)
        )
        rect = pg.Rect(pos, bitmap_left.size)
        rect.w = (
            rect.w +
            bitmap_right.width +
            bitmap_mid.width * length
        )
        rect.w += shadow_offset
        rect.h += shadow_offset
        if save_screen:
            box = self.create_box_internal(rect)
        saved = rect.x
        bitmap_left.blit_to_with_shadow(self.screen, (
            rect.x + shadow_offset,
            rect.y + shadow_offset
        ), True)
        rect.x += bitmap_left.width
        for i in range(length):
            bitmap_mid.blit_to_with_shadow(self.screen, (
                rect.x + shadow_offset,
                rect.y + shadow_offset
            ), True)
            rect.x += bitmap_mid.width
        bitmap_right.blit_to_with_shadow(self.screen, (
            rect.x + shadow_offset,
            rect.y + shadow_offset
        ), True)
        rect.x = saved
        bitmap_left.blit_to(self.screen, rect.topleft)
        rect.x += bitmap_left.width
        for i in range(length):
            bitmap_mid.blit_to(self.screen, rect.topleft)
            rect.x += bitmap_mid.width
        bitmap_right.blit_to(self.screen, rect.topleft)
        rect.x = saved
        return box

    create_box = partialmethod(create_box_with_shadow, shadow_offset=6)

    one_line_box = partialmethod(one_line_box_with_shadow, shadow_offset=6)


class ItemMenuMixin(object):
    def __init__(self):
        self.ball = Ball()
        self.item_flags = 0
        self.num_inventory = 0
        self.last_unequipped_item = 0

    def sell_menu_on_item_change(self, current_item):
        self.one_line_box_with_shadow((100, 150), 5, False, 0)
        self.draw_text(self.words[CASH_LABEL], (110, 160), 0, False, False)
        self.draw_number(self.cash, 6, (149, 164), NumColor.Yellow, NumAlign.Right)
        self.one_line_box_with_shadow((220, 150), 5, False, 0)
        if self.objects[current_item].item.flags & ItemFlag.Sellable:
            self.draw_text(
                self.words[SELLMENU_LABEL_PRICE],
                (230, 160), 0, False, False
            )
            self.draw_number(
                self.objects[current_item].item.price // 2,
                6, (269, 164), NumColor.Yellow, NumAlign.Right
            )

    def sell_menu(self):
        while True:
            w = self.item_select_menu(ItemFlag.Sellable, self.sell_menu_on_item_change)
            if w == 0:
                break
            if self.confirm_menu():
                self.add_item_to_inventory(w, -1)
                self.cash += self.objects[w].item.price // 2

    def buy_menu_on_item_change(self, current_item):
        rect = pg.Rect(20, 8, 300, 175)
        self.sprite_ui[SPRITENUM_ITEMBOX].blit_to(self.screen, (35, 8))
        buf_image = self.ball[self.objects[current_item].item.bitmap]
        if buf_image is not None:
            buf_image.blit_to(self.screen, (42, 16))
        n = 0
        for i in range(MAX_INVENTORY):
            if self.inventory[i].item == 0:
                break
            elif self.inventory[i].item == current_item:
                n = self.inventory[i].amount
                break
        self.one_line_box((20, 105), 5, False)
        self.draw_text(
            self.words[BUYMENU_LABEL_CURRENT],
            (30, 115), 0, False, False
        )
        self.draw_number(
            n, 6, (69, 119), NumColor.Yellow, NumAlign.Right
        )
        self.one_line_box((20, 145), 5, False)
        self.draw_text(
            self.words[CASH_LABEL],
            (30, 155), 0, False, False
        )
        self.draw_number(
            self.cash, 6, (69, 159), NumColor.Yellow, NumAlign.Right
        )
        self.update_screen(rect)

    def buy_menu(self, store_num):
        menu_items = []
        rect = pg.Rect(125, 8, 190, 190)
        y = 22
        for i in range(MAX_STORE_ITEM):
            if self.store[store_num][i] == 0:
                break
            menu_items.append(
                MenuItem(
                    self.store[store_num][i],
                    self.words[self.store[store_num][i]],
                    True, (150, y)
                )
            )
            y += 18
        self.create_box((125, 8), 8, 8, 1, False)
        for y in range(len(menu_items)):
            w = self.objects[menu_items[y].value].item.price
            self.draw_number(
                w, 6, (235, 25 + y * 18),
                NumColor.Cyan, NumAlign.Right
            )
        self.update_screen(rect)
        w = 0
        while True:
            w = self.read_menu(
                menu_items, w, MENUITEM_COLOR,
                self.buy_menu_on_item_change
            )
            if w == MENUITEM_VALUE_CANCELLED:
                break
            if self.objects[w].item.price <= self.cash:
                if self.confirm_menu():
                    self.cash -= self.objects[w].item.price
                    self.add_item_to_inventory(w, 1)
            for y in range(len(menu_items)):
                if w == menu_items[y].value:
                    w = y
                    break

    def equip_item_menu(self, item):
        self.last_unequipped_item = item
        buf_background = partial(self.fbp.render, EQUIPMENU_BACKGROUND_FBPNUM)
        current_player = 0
        selected_color = MENUITEM_COLOR_SELECTED_FIRST
        color_change_time = pg.time.get_ticks() + 600 // MENUITEM_COLOR_SELECTED_TOTALNUM
        while True:
            item = self.last_unequipped_item
            buf_background(self.screen)
            buf_image = self.ball[self.objects[item].item.bitmap]
            if buf_image is not None:
                buf_image.blit_to(
                    self.screen,
                    pal_xy_offset(self.screen_layout.equip_image_box, 8, 8)
                )
            w = self.party[current_player].player_role
            for i in range(MAX_PLAYER_EQUIPMENTS):
                if self.player_roles.equipment[i][w] != 0:
                    self.draw_text(
                        self.words[self.player_roles.equipment[i][w]],
                        self.screen_layout.equip_names[i], MENUITEM_COLOR,
                        True, False
                    )
            self.draw_number(
                self.get_player_attack_strength(w), 4,
                self.screen_layout.equip_status_values[0],
                NumColor.Cyan, NumAlign.Right
            )
            self.draw_number(
                self.get_player_magic_strength(w), 4,
                self.screen_layout.equip_status_values[1],
                NumColor.Cyan, NumAlign.Right
            )
            self.draw_number(
                self.get_player_defense(w), 4,
                self.screen_layout.equip_status_values[2],
                NumColor.Cyan, NumAlign.Right
            )
            self.draw_number(
                self.get_player_dexterity(w), 4,
                self.screen_layout.equip_status_values[3],
                NumColor.Cyan, NumAlign.Right
            )
            self.draw_number(
                self.get_player_flee_rate(w), 4,
                self.screen_layout.equip_status_values[4],
                NumColor.Cyan, NumAlign.Right
            )
            self.create_box(
                self.screen_layout.equip_role_list_box, self.max_party_member_index,
                self.word_max_width(36, 4) - 1, 0, False
            )
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                if current_player == i:
                    if self.objects[item].item.flags & (ItemFlag.EquipableByPlayerRole_First << w):
                        color = selected_color
                    else:
                        color = MENUITEM_COLOR_SELECTED_INACTIVE
                else:
                    if self.objects[item].item.flags & (ItemFlag.EquipableByPlayerRole_First << w):
                        color = MENUITEM_COLOR
                    else:
                        color = MENUITEM_COLOR_INACTIVE
                self.draw_text(
                    self.words[self.player_roles.name[w]],
                    pal_xy_offset(self.screen_layout.equip_role_list_box, 13, 13 + 18 * i),
                    color, True, False
                )
            if item != 0:
                self.draw_text(
                    self.words[item],
                    self.screen_layout.equip_item_name,
                    MENUITEM_COLOR_CONFIRMED, True, False
                )
                self.draw_number(
                    self.get_item_amount(item), 2,
                    self.screen_layout.equip_item_amount,
                    NumColor.Cyan, NumAlign.Right
                )
            self.update_screen()
            self.clear_key_state()
            while True:
                self.process_event()
                if pg.time.get_ticks() >= color_change_time:
                    if selected_color + 1 >= MENUITEM_COLOR_SELECTED_FIRST + MENUITEM_COLOR_SELECTED_TOTALNUM:
                        selected_color = MENUITEM_COLOR_SELECTED_FIRST
                    else:
                        selected_color += 1
                    color_change_time = pg.time.get_ticks() + 600 // MENUITEM_COLOR_SELECTED_TOTALNUM
                    w = self.party[current_player].player_role
                    if self.objects[item].item.flags & (ItemFlag.EquipableByPlayerRole_First << w):
                        self.draw_text(
                            self.words[self.player_roles.name[w]],
                            pal_xy_offset(
                                self.screen_layout.equip_role_list_box,
                                13, 13 + 18 * current_player
                            ), selected_color, True, False
                        )
                if self.input_state.key_press != 0:
                    break
                pg.time.delay(1)
            if item == 0:
                return
            if self.input_state.key_press & (Key.Up | Key.Left):
                current_player = max(current_player - 1, 0)
            elif self.input_state.key_press & (Key.Down | Key.Right):
                current_player = min(current_player + 1, self.max_party_member_index)
            elif self.input_state.key_press & Key.Menu:
                return
            elif self.input_state.key_press & Key.Search:
                w = self.party[current_player].player_role
                if self.objects[item].item.flags & (ItemFlag.EquipableByPlayerRole_First << w):
                    self.objects[item].item.script_on_equip = self.run_trigger_script(
                        self.objects[item].item.script_on_equip, w
                    )

    @static_vars(selected_player=0)
    def item_use_menu(self, item_to_use):
        save = self.item_use_menu.__dict__
        rect = pg.Rect(110, 2, 200, 180)
        selected_color = MENUITEM_COLOR_SELECTED_FIRST
        color_change_time = 0
        while True:
            if save['selected_player'] > self.max_party_member_index:
                selected_color = 0
            self.create_box((110, 2), 7, 9, 0, False)
            self.draw_text(
                self.words[STATUS_LABEL_LEVEL], (200, 16),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_HP], (200, 34),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_MP], (200, 52),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_ATTACKPOWER], (200, 70),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_MAGICPOWER], (200, 88),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_RESISTANCE], (200, 106),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_DEXTERITY], (200, 124),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            self.draw_text(
                self.words[STATUS_LABEL_FLEERATE], (200, 142),
                ITEMUSEMENU_COLOR_STATLABEL, True, False
            )
            i = self.party[save['selected_player']].player_role
            self.draw_number(
                self.player_roles.level[i], 4,
                (240, 20), NumColor.Yellow, NumAlign.Right
            )
            self.sprite_ui[SPRITENUM_SLASH].blit_to(self.screen, (263, 38))
            self.draw_number(
                self.player_roles.max_hp[i], 4,
                (261, 40), NumColor.Blue, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.hp[i], 4,
                (240, 37), NumColor.Yellow, NumAlign.Right
            )
            self.sprite_ui[SPRITENUM_SLASH].blit_to(self.screen, (263, 56))
            self.draw_number(
                self.player_roles.max_mp[i], 4,
                (261, 58), NumColor.Blue, NumAlign.Right
            )
            self.draw_number(
                self.player_roles.mp[i], 4,
                (240, 55), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.get_player_attack_strength(i), 4,
                (240, 74), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.get_player_magic_strength(i), 4,
                (240, 92), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.get_player_defense(i), 4,
                (240, 110), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.get_player_dexterity(i), 4,
                (240, 128), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.get_player_flee_rate(i), 4,
                (240, 146), NumColor.Yellow, NumAlign.Right
            )
            for i in range(self.max_party_member_index + 1):
                if i == save['selected_player']:
                    color = selected_color
                else:
                    color = MENUITEM_COLOR
                self.draw_text(
                    self.words[self.player_roles.name[self.party[i].player_role]],
                    (125, 16 + 20 * i), color, True, False
                )
            self.sprite_ui[SPRITENUM_ITEMBOX].blit_to(self.screen, (120, 80))
            i = self.get_item_amount(item_to_use)
            if i > 0:
                buf_image = self.ball[self.objects[item_to_use].item.bitmap]
                if buf_image is not None:
                    buf_image.blit_to(self.screen, (127, 88))
                self.draw_text(
                    self.words[item_to_use], (116, 143),
                    STATUS_COLOR_EQUIPMENT, True, False
                )
                self.draw_number(
                    i, 2, (170, 133), NumColor.Cyan, NumAlign.Right
                )
            self.update_screen(rect)
            self.clear_key_state()
            while True:
                if pg.time.get_ticks() >= color_change_time:
                    if selected_color + 1 >= MENUITEM_COLOR_SELECTED_FIRST + MENUITEM_COLOR_SELECTED_TOTALNUM:
                        selected_color = MENUITEM_COLOR_SELECTED_FIRST
                    else:
                        selected_color += 1
                    color_change_time = pg.time.get_ticks() + 600 // MENUITEM_COLOR_SELECTED_TOTALNUM
                    w = self.party[save['selected_player']].player_role
                    self.draw_text(
                        self.words[self.player_roles.name[w]],
                        (125, 16 + 20 * save['selected_player']),
                        selected_color, False, True
                    )
                self.process_event()
                if self.input_state.key_press != 0:
                    break
                pg.time.delay(1)
            if i == 0:
                return MENUITEM_VALUE_CANCELLED
            if self.input_state.key_press & (Key.Up | Key.Left):
                if save['selected_player'] > 0:
                    save['selected_player'] -= 1
            elif self.input_state.key_press & (Key.Down | Key.Right):
                if save['selected_player'] < self.max_party_member_index:
                    save['selected_player'] += 1
            elif self.input_state.key_press & Key.Menu:
                break
            elif self.input_state.key_press & Key.Search:
                return self.party[save['selected_player']].player_role
        return MENUITEM_VALUE_CANCELLED

    @static_vars(prev_image_index=0xFFFF, buf_image=None)
    def item_select_menu_update(self):
        save = self.item_select_menu_update.__dict__
        item_delta = 0
        items_per_line = 34 // self.word_length
        item_text_width = 8 * self.word_length + 20
        lines_per_page = 7 - pal_y(self.screen_layout.extra_item_desc_lines)
        cursor_x_offset = self.word_length * 5 // 2
        amount_x_offset = self.word_length * 8 + 1
        page_line_offset = (lines_per_page + 1) // 2
        picture_y_offset = (
            (pal_y(self.screen_layout.extra_item_desc_lines) - 1) * 16
            if pal_y(self.screen_layout.extra_item_desc_lines) > 1
            else 0
        )

        if self.input_state.key_press & Key.Up:
            item_delta = -items_per_line
        elif self.input_state.key_press & Key.Down:
            item_delta = items_per_line
        elif self.input_state.key_press & Key.Left:
            item_delta = -1
        elif self.input_state.key_press & Key.Right:
            item_delta = 1
        elif self.input_state.key_press & Key.PgUp:
            item_delta = -(items_per_line * lines_per_page)
        elif self.input_state.key_press & Key.PgDn:
            item_delta = items_per_line * lines_per_page
        elif self.input_state.key_press & Key.Home:
            item_delta = -self.cur_inv_menu_item
        elif self.input_state.key_press & Key.End:
            item_delta = self.num_inventory - self.cur_inv_menu_item - 1
        elif self.input_state.key_press & Key.Menu:
            return 0
        else:
            item_delta = 0

        if 0 <= self.cur_inv_menu_item + item_delta < self.num_inventory:
            self.cur_inv_menu_item += item_delta

        self.create_box_with_shadow(
            (2, 0), lines_per_page - 1, 17, 1, False, 0
        )
        i = self.cur_inv_menu_item // items_per_line * \
            items_per_line - items_per_line * page_line_offset
        if i < 0:
            i = 0
        j = 0

        while j < lines_per_page:
            k = 0
            while k < items_per_line:
                obj = self.inventory[i].item
                color = MENUITEM_COLOR
                if i >= MAX_INVENTORY or obj == 0:
                    j = lines_per_page
                    break
                if i == self.cur_inv_menu_item:
                    if (not (
                            self.objects[obj].item.flags & self.item_flags
                    ) or (
                            short(self.inventory[i].amount) <=
                            short(self.inventory[i].amount_in_use)
                    )):
                        color = MENUITEM_COLOR_SELECTED_INACTIVE
                    else:
                        if self.inventory[i].amount == 0:
                            color = MENUITEM_COLOR_EQUIPPEDITEM
                        else:
                            color = menuitem_color_selected()
                elif (not (
                        self.objects[obj].item.flags & self.item_flags
                ) or (
                              short(self.inventory[i].amount) <=
                              short(self.inventory[i].amount_in_use)
                )):
                    color = MENUITEM_COLOR_INACTIVE
                elif self.inventory[i].amount == 0:
                    color = MENUITEM_COLOR_EQUIPPEDITEM

                self.draw_text(
                    self.words[obj], (15 + k * item_text_width, 12 + j * 18),
                    color, True, False
                )
                if i == self.cur_inv_menu_item:
                    self.sprite_ui[SPRITENUM_CURSOR].blit_to(
                        self.screen,
                        (15 + cursor_x_offset + k * item_text_width, 22 + j * 18)
                    )
                if (
                    short(self.inventory[i].amount) -
                    short(self.inventory[i].amount_in_use)
                ) > 1:
                    self.draw_number(
                        self.inventory[i].amount - self.inventory[i].amount_in_use,
                        2, (15 + amount_x_offset + k *
                            item_text_width, 17 + j * 18),
                        NumColor.Cyan, NumAlign.Right
                    )
                i += 1
                k += 1
            j += 1
        x_base = 0
        y_base = 140
        self.sprite_ui[SPRITENUM_ITEMBOX].blit_to_with_shadow(
            self.screen,
            (x_base, y_base + 5 - picture_y_offset), True
        )
        self.sprite_ui[SPRITENUM_ITEMBOX].blit_to(
            self.screen, (x_base, y_base - picture_y_offset)
        )
        if self.cur_inv_menu_item >= 0:
            obj = self.inventory[self.cur_inv_menu_item].item
            if self.objects[obj].item.bitmap != save['prev_image_index']:
                save['buf_image'] = self.ball[self.objects[obj].item.bitmap]
                if save['buf_image'] is not None:
                    save['prev_image_index'] = self.objects[obj].item.bitmap
                else:
                    save['prev_image_index'] = 0xFFFF
        else:
            obj = 0xFFFF
        if save['prev_image_index'] != 0xFFFF:
            save['buf_image'].blit_to(
                self.screen, (x_base + 8, y_base + 7 - picture_y_offset)
            )

        if not is_win95:
            if not self.no_desc and self.descs is not None:
                d = self.descs[obj]
                if d is not None:
                    k = 150
                    parts = d.split('*')
                    for part in parts:
                        self.draw_text(
                            part, (75, k), DESCTEXT_COLOR, True, False)
                        k += 16
        else:
            if not self.no_desc:
                script = self.objects[obj].item.script_desc
                line = 0
                while script and self.scripts[script].op != 0:
                    if self.scripts[script].op == 0xFFFF:
                        line_incr = bool(self.scripts[script].p2 != 1)
                        script = self.run_auto_script(script, PAL_ITEM_DESC_BOTTOM | line)
                        line += line_incr
                    else:
                        script = self.run_auto_script(script, 0)

        if self.input_state.key_press & Key.Search:
            if (
                self.objects[obj].item.flags & self.item_flags and
                short(self.inventory[self.cur_inv_menu_item].amount) >
                short(self.inventory[self.cur_inv_menu_item].amount_in_use)
            ):
                if self.inventory[self.cur_inv_menu_item].amount > 0:
                    j = self.cur_inv_menu_item // items_per_line if self.cur_inv_menu_item < items_per_line * \
                                                                    page_line_offset else page_line_offset
                    k = self.cur_inv_menu_item % items_per_line
                    self.draw_text(
                        self.words[obj], (15 + k * item_text_width, 12 + j * 18),
                        MENUITEM_COLOR_CONFIRMED, False, False
                    )
                return obj
        return 0xFFFF

    def item_select_menu_init(self, item_flags):
        self.item_flags = item_flags
        self.compress_inventory()
        self.num_inventory = 0
        while (
                self.num_inventory < MAX_INVENTORY and
                self.inventory[self.num_inventory].item != 0
        ):
            self.num_inventory += 1
        if (self.item_flags & ItemFlag.Usable) and not self.in_battle:
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                for j in range(MAX_PLAYER_EQUIPMENTS):
                    if self.objects[self.player_roles.equipment[j][w]].item.flags & ItemFlag.Usable:
                        if self.num_inventory < MAX_INVENTORY:
                            self.inventory[self.num_inventory].item = self.player_roles.equipment[j][w]
                            self.inventory[self.num_inventory].amount = 0
                            self.inventory[self.num_inventory].amount_in_use = 0xFFFF
                            self.num_inventory += 1

    def item_select_menu(self, item_flags, callback=None):
        self.item_select_menu_init(item_flags)
        prev_index = self.cur_inv_menu_item
        self.clear_key_state()
        if callback is not None:
            self.no_desc = True
            callback(self.inventory[self.cur_inv_menu_item].item)
        ticks = pg.time.get_ticks()
        while True:
            if callback is None:
                self.make_scene()
            w = self.item_select_menu_update()
            self.update_screen()
            self.clear_key_state()
            self.process_event()
            while pg.time.get_ticks() <= ticks:
                self.process_event()
                if self.input_state.key_press != 0:
                    break
                pg.time.delay(5)
            ticks = pg.time.get_ticks() + FRAME_TIME
            if w != 0xFFFF:
                self.no_desc = False
                return w
            if prev_index != self.cur_inv_menu_item:
                if 0 <= self.cur_inv_menu_item < MAX_INVENTORY:
                    if callback is not None:
                        callback(self.inventory[self.cur_inv_menu_item].item)
                prev_index = self.cur_inv_menu_item


class MagicMenuMixin(object):
    def __init__(self):
        self.cur_magic_menu_item = 0
        self.magic_items = [MagicItem() for _ in range(MAX_PLAYER_MAGICS)]
        self.num_magic = 0
        self.player_mp = 0

    @static_vars(w=0)
    def ingame_magic_menu(self):
        save = self.ingame_magic_menu.__dict__
        rect = pg.Rect(35, 62, 285, 90)
        y = 45
        for i in range(self.max_party_member_index + 1):
            self.player_info_box(
                (y, 165), self.party[i].player_role, True
            )
            y += 78
        menu_items = []
        y = 75
        for i in range(self.max_party_member_index + 1):
            assert i <= MAX_PLAYERS_IN_PARTY
            player_role = self.party[i].player_role
            menu_items.append(
                MenuItem(
                    i, self.words[self.player_roles.name[player_role]],
                    self.player_roles.hp[player_role] > 0, (48, y)
                )
            )
            y += 18
        self.create_box(
            (35, 62), self.max_party_member_index,
            self.menu_text_max_width(menu_items) - 1, 0, False
        )
        self.update_screen(rect)
        save['w'] = self.read_menu(menu_items, save['w'], MENUITEM_COLOR)
        if save['w'] == MENUITEM_VALUE_CANCELLED:
            return
        magic = 0
        while True:
            magic = self.magic_selection_menu(self.party[save['w']].player_role, False, magic)
            if magic == 0:
                break
            if self.objects[magic].magic.flags & MagicFlag.ApplyToAll:
                self.objects[magic].magic.script_on_use = self.run_trigger_script(
                    self.objects[magic].magic.script_on_use, 0
                )
                if RunResult.success:
                    self.objects[magic].magic.script_on_success = self.run_trigger_script(
                        self.objects[magic].magic.script_on_success, 0
                    )
                    self.player_roles.mp[self.party[save['w']].player_role] -= self.magics[self.objects[magic].magic.magic_number].cost_mp
                if self.need_fadein:
                    self.fadein(1)
                    self.need_fadein = False
            else:
                player = 0
                rect = pg.Rect(0, 193, 9, 6)
                while player != MENUITEM_VALUE_CANCELLED:
                    y = 45
                    for i in range(self.max_party_member_index + 1):
                        self.player_info_box(
                            (y, 165), self.party[i].player_role,  True
                        )
                        y += 78
                    rect.x = 70 + 78 * player
                    self.sprite_ui[SPRITENUM_CURSOR].blit_to(self.screen, rect.topleft)
                    self.update_screen(rect)
                    while True:
                        self.clear_key_state()
                        self.process_event()
                        if self.input_state.key_press & Key.Menu:
                            player = MENUITEM_VALUE_CANCELLED
                            break
                        elif self.input_state.key_press & Key.Search:
                            self.objects[magic].magic.script_on_use = self.run_trigger_script(
                                self.objects[magic].magic.script_on_use,
                                self.party[player].player_role
                            )
                            if RunResult.success:
                                self.objects[magic].magic.script_on_success = self.run_trigger_script(
                                    self.objects[magic].magic.script_on_success,
                                    self.party[player].player_role
                                )
                                if RunResult.success:
                                    self.player_roles.mp[self.party[save['w']].player_role] -= \
                                    self.magics[self.objects[magic].magic.magic_number].cost_mp
                                    if (
                                        self.player_roles.mp[self.party[save['w']].player_role] <
                                        self.magics[self.objects[magic].magic.magic_number].cost_mp
                                    ):
                                        player = MENUITEM_VALUE_CANCELLED
                            break
                        elif self.input_state.key_press & (Key.Left | Key.Up):
                            if player > 0:
                                player -= 1
                                break
                        elif self.input_state.key_press & (Key.Right | Key.Down):
                            if player < self.max_party_member_index:
                                player += 1
                                break
                        pg.time.delay(1)
            y = 45
            for i in range(self.max_party_member_index + 1):
                self.player_info_box(
                    (y, 165), self.party[i].player_role, True
                )
                y += 78

    def magic_selection_menu_update(self):
        item_delta = 0
        items_per_line = 32 // self.word_length
        item_text_width = 8 * self.word_length + 7
        lines_per_page = 5 - pal_y(self.screen_layout.extra_magic_desc_lines)
        box_y_offset = pal_y(self.screen_layout.extra_magic_desc_lines) * 16
        cursor_x_offset = self.word_length * 5 // 2
        page_line_offset = lines_per_page // 2

        if self.input_state.key_press & Key.Up:
            item_delta = -items_per_line
        elif self.input_state.key_press & Key.Down:
            item_delta = items_per_line
        elif self.input_state.key_press & Key.Left:
            item_delta = -1
        elif self.input_state.key_press & Key.Right:
            item_delta = 1
        elif self.input_state.key_press & Key.PgUp:
            item_delta = -(items_per_line * lines_per_page)
        elif self.input_state.key_press & Key.PgDn:
            item_delta = items_per_line * lines_per_page
        elif self.input_state.key_press & Key.Home:
            item_delta = -self.cur_magic_menu_item
        elif self.input_state.key_press & Key.End:
            item_delta = self.num_magic - self.cur_magic_menu_item - 1
        elif self.input_state.key_press & Key.Menu:
            return 0
        else:
            item_delta = 0
        
        if 0 <= self.cur_magic_menu_item + item_delta < self.num_magic:
            self.cur_magic_menu_item += item_delta
        
        self.create_box_with_shadow(
            (10, 42 + box_y_offset), lines_per_page - 1,
            16, 1, False, 0
        )
        if not is_win95:
            if self.descs is None:
                self.one_line_box((0, 0), 5, False)
                self.draw_text(
                    self.words[CASH_LABEL], (10, 10),
                    0, False, False
                )
                self.draw_number(
                    self.cash, 6, (49, 14),
                    NumColor.Yellow, NumAlign.Right
                )

                self.one_line_box((215, 0), 5, False)
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (260, 14)
                )
                self.draw_number(
                    self.magic_items[self.cur_magic_menu_item].mp, 4,
                    (230, 14), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    self.player_mp, 4, (265, 14),
                    NumColor.Cyan, NumAlign.Right
                )
            else:
                d = self.descs[self.magic_items[self.cur_magic_menu_item].magic]
                if d is not None:
                    k = 3
                    for line in d.split('*'):
                        self.draw_text(
                            line, (102, k), DESCTEXT_COLOR,
                            True, False
                        )
                        k += 16
                self.one_line_box((0, 0), 5, False)
                self.sprite_ui[SPRITENUM_SLASH].blit_to(
                    self.screen, (45, 14)
                )
                self.draw_number(
                    self.magic_items[self.cur_magic_menu_item].mp, 4,
                    (15, 14), NumColor.Yellow, NumAlign.Right
                )
                self.draw_number(
                    self.player_mp, 4, (50, 14),
                    NumColor.Cyan, NumAlign.Right
                )
        else:
            script = self.objects[self.magic_items[self.cur_magic_menu_item].magic].item.script_desc
            line = 0
            while script and self.scripts[script].op != 0:
                if self.scripts[script].op == 0xFFFF:
                    line_incr = bool(self.scripts[script].p2 != 1)
                    script = self.run_auto_script(script, line)
                    line += line_incr
                else:
                    script = self.run_auto_script(script, 0)
            self.one_line_box((0, 0), 5, False)
            self.sprite_ui[SPRITENUM_SLASH].blit_to(self.screen, (45, 14))
            self.draw_number(
                self.magic_items[self.cur_magic_menu_item].mp, 4,
                (15, 14), NumColor.Yellow, NumAlign.Right
            )
            self.draw_number(
                self.player_mp, 4, (50, 14), NumColor.Cyan, NumAlign.Right
            )

        i = (self.cur_magic_menu_item // items_per_line - page_line_offset) * items_per_line
        if i < 0:
            i = 0
        j = 0
        while j < lines_per_page:
            k = 0
            while k < items_per_line:
                color = MENUITEM_COLOR
                if i >= self.num_magic:
                    j = lines_per_page
                    break
                if i == self.cur_magic_menu_item:
                    if self.magic_items[i].enabled:
                        color = menuitem_color_selected()
                    else:
                        color = MENUITEM_COLOR_SELECTED_INACTIVE
                elif not self.magic_items[i].enabled:
                    color = MENUITEM_COLOR_INACTIVE
                self.draw_text(
                    self.words[self.magic_items[i].magic],
                    (35 + k * item_text_width, 54 + j * 18 + box_y_offset),
                    color, True, False
                )
                if i == self.cur_magic_menu_item:
                    self.sprite_ui[SPRITENUM_CURSOR].blit_to(
                        self.screen, (
                            35 + cursor_x_offset + k * item_text_width,
                            64 + j * 18 + box_y_offset
                        )
                    )
                i += 1
                k += 1
            j += 1
        if self.input_state.key_press & Key.Search:
            if self.magic_items[self.cur_magic_menu_item].enabled:
                j = self.cur_magic_menu_item % items_per_line
                k = self.cur_magic_menu_item // items_per_line if self.cur_magic_menu_item < items_per_line * page_line_offset else page_line_offset
                j = 35 + j * item_text_width
                k = 54 + k * 18 + box_y_offset
                self.draw_text(
                    self.words[self.magic_items[self.cur_magic_menu_item].magic],
                    (j, k), MENUITEM_COLOR_CONFIRMED, False, True
                )
                return self.magic_items[self.cur_magic_menu_item].magic
        return 0xFFFF

    def magic_selection_menu_init(self, player_role, in_battle, default_magic):
        self.cur_magic_menu_item = 0
        self.num_magic = 0
        self.player_mp = self.player_roles.mp[player_role]
        for i in range(MAX_PLAYER_MAGICS):
            w = self.player_roles.magic[i][player_role]
            if w != 0:
                self.magic_items[self.num_magic].magic = w
                w = self.objects[w].magic.magic_number
                self.magic_items[self.num_magic].mp = self.magics[w].cost_mp
                self.magic_items[self.num_magic].enabled = (
                    False if
                    self.magic_items[self.num_magic].mp > self.player_mp
                    else True
                )
                w = self.objects[self.magic_items[self.num_magic].magic].magic.flags
                if in_battle:
                    if not w & MagicFlag.UsableInBattle:
                        self.magic_items[self.num_magic].enabled = False
                else:
                    if not w & MagicFlag.UsableOutsideBattle:
                        self.magic_items[self.num_magic].enabled = False
                self.num_magic += 1
        for i in range(self.num_magic - 1):
            completed = True
            for j in range(self.num_magic - i - 1):
                if self.magic_items[j].magic > self.magic_items[i].magic:
                    self.magic_items[j] , self.magic_items[j + 1] = self.magic_items[j + 1] , self.magic_items[j]
                    completed = False
            if completed:
                break
        for i in range(self.num_magic):
            if self.magic_items[i].magic == default_magic:
                self.cur_magic_menu_item = i
                break

    def magic_selection_menu(self, player_role, in_battle, default_magic):
        self.magic_selection_menu_init(player_role, in_battle, default_magic)
        self.clear_key_state()
        ticks = pg.time.get_ticks()
        while True:
            self.make_scene()
            w = 45
            for i in range(self.max_party_member_index + 1):
                self.player_info_box(
                    (w, 165), self.party[i].player_role, False
                )
                w += 78
            w = self.magic_selection_menu_update()
            self.update_screen()
            self.clear_key_state()
            if w != 0xFFFF:
                return w
            self.process_event()
            while pg.time.get_ticks() < ticks:
                self.process_event()
                if self.input_state.key_press != 0:
                    break
                pg.time.delay(5)
            ticks = pg.time.get_ticks() + FRAME_TIME
        return 0


class UIMenuMixin(ItemMenuMixin, MagicMenuMixin):
    def __init__(self):
        self.cur_main_menu_item = 0
        self.cur_sys_menu_item = 0
        self.cur_inv_menu_item = 0

    def system_menu_on_item_change(self, current_item):
        self.cur_sys_menu_item = current_item - 1

    def system_menu(self):
        rect = pg.Rect(40, 60, 280, 135)
        system_menu_items = [
            MenuItem(1, self.words[SYSMENU_LABEL_SAVE], True, (53, 72)),
            MenuItem(2, self.words[SYSMENU_LABEL_LOAD], True, (53, 72 + 18)),
            MenuItem(3, self.words[SYSMENU_LABEL_MUSIC], True, (53, 72 + 36)),
            MenuItem(4, self.words[SYSMENU_LABEL_SOUND], True, (53, 72 + 54)),
            MenuItem(5, self.words[SYSMENU_LABEL_QUIT], True, (53, 72 + 72)),
        ]
        menu_box = self.create_box(
            (40, 60), len(system_menu_items) - 1,
                      self.menu_text_max_width(system_menu_items) - 1, 0, True
        )
        self.update_screen(rect)
        result = self.read_menu(system_menu_items, self.cur_sys_menu_item, MENUITEM_COLOR, self.system_menu_on_item_change)
        if result == MENUITEM_VALUE_CANCELLED:
            self.delete_box(menu_box)
            self.update_screen(rect)
            return False
        if result == 1:
            slot = self.save_slot_menu(self.cur_save_slot)
            if slot != MENUITEM_VALUE_CANCELLED:
                self.cur_save_slot = slot
                saved_times = max(self.get_saved_times(i) for i in range(1, 6))
                self.save_game(slot, saved_times + 1)
        elif result == 2:
            slot = self.save_slot_menu(self.cur_save_slot)
            if slot != MENUITEM_VALUE_CANCELLED:
                self.play_music(0, False, 1)
                self.fadeout(1)
                self.init_game_data(slot)
        elif result == 3:
            self.on_off_music(self.switch_menu(config['enable_music']))
        elif result == 4:
            config['enable_sound'] = self.switch_menu(config['enable_sound'])
        elif result == 5:
            self.quit()

        self.delete_box(menu_box)
        return True

    @static_vars(w=1)
    def inventory_menu(self):
        save = self.inventory_menu.__dict__
        rect = pg.Rect(30, 60, 290, 60)
        menu_items = [
            MenuItem(
                1, self.words[INVMENU_LABEL_USE],
                True, (43, 73)
            ),
            MenuItem(
                2, self.words[INVMENU_LABEL_EQUIP],
                True, (43, 73 + 18)
            )
        ]
        self.create_box(
            (30, 60), 1,
            self.menu_text_max_width(menu_items) - 1,
            0, False
        )
        self.update_screen(rect)
        save['w'] = self.read_menu(
            menu_items, save['w'] - 1, MENUITEM_COLOR
        )
        if save['w'] == 1:
            self.use_item()
        elif save['w'] == 2:
            self.equip_item()

    def ingame_menu_on_item_change(self, current_item):
        self.cur_main_menu_item = current_item - 1

    def ingame_menu(self):
        rect = pg.Rect(0, 0, 320, 185)
        self.screen_bak.blit(self.screen, (0, 0))
        main_menu_items = [
            MenuItem(1, self.words[GAMEMENU_LABEL_STATUS], True, (16, 50)),
            MenuItem(2, self.words[GAMEMENU_LABEL_MAGIC], True, (16, 50 + 18)),
            MenuItem(3, self.words[GAMEMENU_LABEL_INVENTORY], True, (16, 50 + 36)),
            MenuItem(4, self.words[GAMEMENU_LABEL_SYSTEM], True, (16, 50 + 54))
        ]
        cash_box = self.show_cash(self.cash)
        menu_box = self.create_box((3, 37), 3, self.menu_text_max_width(main_menu_items) - 1, 0, False)
        self.update_screen(rect)
        while True:
            result = self.read_menu(
                main_menu_items, self.cur_main_menu_item,
                MENUITEM_COLOR, self.ingame_menu_on_item_change
            )
            if result == MENUITEM_VALUE_CANCELLED:
                break
            if result == 1:
                self.show_player_status()
                break
            elif result == 2:
                self.ingame_magic_menu()
                break
            elif result == 3:
                self.inventory_menu()
                break
            elif result == 4:
                self.system_menu()
                break
        self.delete_box(cash_box)
        self.delete_box(menu_box)
        self.blit(self.screen_bak, (0, 0))

    def opening_menu(self):
        cur_item = 0
        items = [MenuItem(0, self.words[MAINMENU_LABEL_NEWGAME], True, (125, 95)),
                 MenuItem(1, self.words[MAINMENU_LABEL_LOADGAME], True, (125, 112))]
        self.play_music(RIX_NUM_OPENINGMENU, True, 1)

        self.fbp.render(MAINMENU_BACKGROUND_FBPNUM, self.screen)
        self.update_screen()
        self.fadein(1)
        while True:
            selected = self.read_menu(items, cur_item, MENUITEM_COLOR)
            if selected in {0, MENUITEM_VALUE_CANCELLED}:
                selected = 0
                break
            elif selected == 1:
                self.screen_bak.blit(self.screen, (0, 0))
                selected = self.save_slot_menu(1)
                self.blit(self.screen_bak, (0, 0))
                self.update_screen()
                if selected != MENUITEM_VALUE_CANCELLED:
                    break
                cur_item = 1
        self.play_music(0, False, 1)
        self.fadeout(1)
        if is_win95 and selected == 0:
            self.play_video('3.AVI')
        return selected

    def selection_menu(self, items, default):
        w = [(self.text_width(items[i]) + 8) >> 4 if len(items) > i else 1 for i in range(4)]
        dx = [(i - 1) * 16 for i in w]
        positions = [
            (145, 110),
            (220 + dx[0], 110),
            (145, 160),
            (220 + dx[2], 160)
        ]
        rect = pg.Rect(130, 100, 125 + max(dx[0] + dx[1], dx[2] + dx[3]), 100)
        menu_items = [
            MenuItem(
                enabled=True,
                pos=positions[i],
                label=text,
                value=i
            ) for i, text in enumerate(items)
        ]
        dx[1] = dx[0]
        dx[3] = dx[2]
        dx[0] = dx[2] = 0
        boxes = [
            self.one_line_box(
                (130 + 75 * (i % 2) + dx[i], 100 + 50 * (i // 2)),
                w[i] + 1, True
            )
            for i in range(len(items))
        ]
        self.update_screen(rect)
        result = self.read_menu(menu_items, default, MENUITEM_COLOR)
        for i in boxes:
            self.delete_box(i)
        self.update_screen(rect)
        return result

    def confirm_menu(self):
        items = [
            self.words[CONFIRMMENU_LABEL_NO],
            self.words[CONFIRMMENU_LABEL_YES],
        ]
        result = self.selection_menu(items, 0)
        return (result != MENUITEM_VALUE_CANCELLED and result != 0)

    def switch_menu(self, enabled):
        items = [
            self.words[SWITCHMENU_LABEL_DISABLE],
            self.words[SWITCHMENU_LABEL_ENABLE],
        ]
        result = self.selection_menu(items, enabled)
        return enabled if result == MENUITEM_VALUE_CANCELLED else result != 0

    def save_slot_menu(self, default_slot):
        w = self.word_max_width(LOADMENU_LABEL_SLOT_FIRST, 5)
        dx = max((w - 4) * 16, 0)
        rect = pg.Rect(195 - dx, 7, 120 + dx, 190)
        menu_items = [
            MenuItem(
                i + 1,
                self.words[LOADMENU_LABEL_SLOT_FIRST + i],
                True, (210 - dx, 17 + 38 * i)
            )
            for i in range(5)
        ]
        boxes = [
            self.one_line_box((195 - dx, 7 + 38 * i), 6 + max(w - 4, 0), False)
            for i in range(5)
        ]
        for i in range(1, 6):
            self.draw_number(
                self.get_saved_times(i), 4,
                (270, 38 * i - 17),
                NumColor.Yellow, NumAlign.Right
            )
        self.update_screen(rect)
        item_selected = self.read_menu(menu_items, default_slot - 1, MENUITEM_COLOR)
        for box in boxes:
            self.delete_box(box)
        self.update_screen(rect)
        return item_selected

    def read_menu(self, items, cur_item, label_color, onchange_callback=None):
        if cur_item >= len(items):
            cur_item = 0
        for i, item in enumerate(items):
            color = label_color
            if not item.enabled:
                if i == cur_item:
                    color = MENUITEM_COLOR_SELECTED_INACTIVE
                else:
                    color = MENUITEM_COLOR_INACTIVE
            self.draw_text(item.label, item.pos, color, True, True)

        if callable(onchange_callback):
            onchange_callback(items[cur_item].value)
        while True:
            self.clear_key_state()
            if items[cur_item].enabled:
                item = items[cur_item]
                self.draw_text(item.label, item.pos,
                               menuitem_color_selected(), False, True)
            self.process_event()
            if self.input_state.key_press & (Key.Down | Key.Right):
                item = items[cur_item]
                color = label_color if item.enabled else MENUITEM_COLOR_INACTIVE
                self.draw_text(item.label, item.pos, color, False, True)
                cur_item = (cur_item + 1) % len(items)
                item = items[cur_item]
                color = menuitem_color_selected() if item.enabled else MENUITEM_COLOR_INACTIVE
                self.draw_text(item.label, item.pos, color, False, True)
                if callable(onchange_callback):
                    onchange_callback(item.value)
            elif self.input_state.key_press & (Key.Up | Key.Left):
                item = items[cur_item]
                color = label_color if item.enabled else MENUITEM_COLOR_INACTIVE
                self.draw_text(item.label, item.pos, color, False, True)
                cur_item = (cur_item - 1) % len(items)
                item = items[cur_item]
                color = menuitem_color_selected() if item.enabled else MENUITEM_COLOR_INACTIVE
                self.draw_text(item.label, item.pos, color, False, True)
                if callable(onchange_callback):
                    onchange_callback(item.value)
            elif self.input_state.key_press & Key.Menu:
                item = items[cur_item]
                color = label_color if item.enabled else MENUITEM_COLOR_INACTIVE
                self.draw_text(item.label, item.pos, color, False, True)
                break
            elif self.input_state.key_press & Key.Search:
                if items[cur_item].enabled:
                    item = items[cur_item]
                    self.draw_text(item.label, item.pos,
                                   MENUITEM_COLOR_CONFIRMED, False, True)
                    return item.value
            pg.time.delay(50)
        return MENUITEM_VALUE_CANCELLED


class UIBattleMixin(object):
    def __init__(self):
        self.cur_misc_menu_item = 0
        self.cur_sub_menu_item = 0

    def battle_ui_update_end(self):
        for i in range(BATTLEUI_MAX_SHOWNUM):
            if self.battle.ui.show_nums[i].num > 0:
                if (pg.time.get_ticks() - self.battle.ui.show_nums[i].time) / BATTLE_FRAME_TIME > 10:
                    self.battle.ui.show_nums[i].num = 0
                else:
                    self.draw_number(
                        self.battle.ui.show_nums[i].num, 5,
                        (
                            pal_x(self.battle.ui.show_nums[i].pos),
                            pal_y(self.battle.ui.show_nums[i].pos) - (pg.time.get_ticks() - self.battle.ui.show_nums[i].time) // BATTLE_FRAME_TIME
                        ), self.battle.ui.show_nums[i].color, NumAlign.Right
                    )
        self.clear_key_state()

    @static_vars(frame=0)
    def battle_ui_update(self):
        save = self.battle_ui_update.__dict__
        save['frame'] += 1
        if self.battle.ui.auto_attack and not self.auto_battle:
            if self.input_state.key_press & Key.Menu:
                self.battle.ui.auto_attack = False
            else:
                item_text = self.words[BATTLEUI_LABEL_AUTO]
                self.draw_text(
                    item_text, (312 - self.text_width(item_text), 10),
                    MENUITEM_COLOR_CONFIRMED, True, False
                )
        if self.auto_battle:
            self.battle_player_check_ready()
            for i in range(self.max_party_member_index + 1):
                if self.battle.players[i].state == FighterState.Com:
                    self.battle_ui_player_ready(i)
                    break
            if self.battle.ui.state != BattleUIState.Wait:
                w = self.battle_ui_pick_up_auto_magic(
                    self.party[self.battle.ui.cur_player_index].player_role,
                    9999
                )
                if w == 0:
                    self.battle.ui.action_type = BattleActionType.Attack
                    self.battle.ui.selected_index = self.battle_select_auto_target()
                else:
                    self.battle.ui.action_type = BattleActionType.Magic
                    self.battle.ui.object_id = w
                    if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                        self.battle.ui.selected_index = -1
                    else:
                        self.battle.ui.selected_index = self.battle_select_auto_target()
                self.battle_commit_action(False)
            return self.battle_ui_update_end()
        if self.input_state.key_press & Key.Auto:
            self.battle.ui.auto_attack = not self.battle.ui.auto_attack
            self.battle.ui.menu_state = BattleMenuState.Main
        if self.battle.phase == BattlePhase.PerformAction:
            return self.battle_ui_update_end()
        if not self.battle.ui.auto_attack:
            for i in range(self.max_party_member_index + 1):
                player_role = self.party[i].player_role
                if (
                    self.player_status[player_role][Status.Sleep] != 0 or
                    self.player_status[player_role][Status.Confused] != 0 or
                    self.player_status[player_role][Status.Puppet] != 0
                ):
                    w = 0
                self.player_info_box(
                    (91 + 77 * i, 165), player_role, False
                )
        if self.input_state.key_press & Key.Status:
            self.show_player_status()
            return self.battle_ui_update_end()
        if self.battle.ui.state != BattleUIState.Wait:
            player_role = self.party[self.battle.ui.cur_player_index].player_role
            if (
                self.player_roles.hp[player_role] == 0 and
                self.player_status[player_role][Status.Puppet]
            ):
                self.battle.ui.action_type = BattleActionType.Attack
                if self.player_can_attack_all(player_role):
                    self.battle.ui.selected_index = -1
                else:
                    self.battle.ui.selected_index = self.battle_select_auto_target()
                self.battle_commit_action(False)
                return self.battle_ui_update_end()
            if (
                self.player_roles.hp[player_role] == 0 or
                self.player_status[player_role][Status.Sleep] != 0 or
                self.player_status[player_role][Status.Paralyzed] != 0
            ):
                self.battle.ui.action_type = BattleActionType.Pass
                self.battle_commit_action(False)
                return self.battle_ui_update_end()
            if self.player_status[player_role][Status.Confused]:
                self.battle.ui.action_type = BattleActionType.AttackMate
                self.battle_commit_action(False)
                return self.battle_ui_update_end()
            if self.battle.ui.auto_attack:
                self.battle.ui.action_type = BattleActionType.Attack
                if self.player_can_attack_all(player_role):
                    self.battle.ui.selected_index = -1
                else:
                    self.battle.ui.selected_index = self.battle_select_auto_target()
                self.battle_commit_action(False)
                return self.battle_ui_update_end()
            i = SPRITENUM_BATTLE_ARROW_CURRENTPLAYER_RED
            if save['frame'] & 1:
                i = SPRITENUM_BATTLE_ARROW_CURRENTPLAYER
            x = pal_x(player_pos[self.max_party_member_index][self.battle.ui.cur_player_index]) - 8
            y = pal_y(player_pos[self.max_party_member_index]
                      [self.battle.ui.cur_player_index]) - 74
            self.sprite_ui[i].blit_to(self.screen, (x, y))
        if self.battle.ui.state == BattleUIState.Wait:
            if not self.battle.enemy_cleared:
                self.battle_player_check_ready()
                for i in range(self.max_party_member_index + 1):
                    if self.battle.players[i].state == FighterState.Com:
                        self.battle_ui_player_ready(i)
                        break
        elif self.battle.ui.state == BattleUIState.SelectMove:
            Item = attr.make_class(
                'Item',
                {
                    'sprite_num': attr.ib(factory=int),
                    'pos': attr.ib(default=(0, 0)),
                    'action': attr.ib(converter=BattleUIAction, default=0)
                }
            )
            items = [
                Item(
                    SPRITENUM_BATTLEICON_ATTACK, (27, 140),
                    BattleUIAction.Attack
                ),
                Item(
                    SPRITENUM_BATTLEICON_MAGIC, (0, 155),
                    BattleUIAction.Magic
                ),
                Item(
                    SPRITENUM_BATTLEICON_COOPMAGIC, (54, 155),
                    BattleUIAction.CoopMagic
                ),
                Item(
                    SPRITENUM_BATTLEICON_MISCMENU, (27, 170),
                    BattleUIAction.Misc
                )
            ]
            if self.battle.ui.menu_state == BattleMenuState.Main:
                if self.input_state.curdir == Direction.North:
                    self.battle.ui.selected_action = 0
                elif self.input_state.curdir == Direction.South:
                    self.battle.ui.selected_action = 3
                elif self.input_state.curdir == Direction.West:
                    if self.battle_ui_is_action_valid(BattleUIAction.Magic):
                        self.battle.ui.selected_action = 1
                elif self.input_state.curdir == Direction.East:
                    if self.battle_ui_is_action_valid(BattleUIAction.CoopMagic):
                        self.battle.ui.selected_action = 2
            if not self.battle_ui_is_action_valid(items[self.battle.ui.selected_action].action):
                self.battle.ui.selected_action = 0
            for i, item in enumerate(items):
                if self.battle.ui.selected_action == i:
                    self.sprite_ui[item.sprite_num].blit_to(
                        self.screen, item.pos
                    )
                elif self.battle_ui_is_action_valid(item.action):
                    self.sprite_ui[item.sprite_num].blit_mono_color(
                        self.screen, item.pos, -4, 0
                    )
                else:
                    self.sprite_ui[item.sprite_num].blit_mono_color(
                        self.screen, item.pos, -4, 0x10
                    )
            if self.battle.ui.menu_state == BattleMenuState.Main:
                if self.input_state.key_press & Key.Search:
                    if self.battle.ui.selected_action == 0:
                        self.battle.ui.action_type = BattleActionType.Attack
                        if self.player_can_attack_all(self.party[self.battle.ui.cur_player_index].player_role):
                            self.battle.ui.state = BattleUIState.SelectTargetEnemyAll
                        else:
                            if self.battle.ui.prev_enemy_target != -1:
                                self.battle.ui.selected_index = self.battle.ui.prev_enemy_target
                            self.battle.ui.state = BattleUIState.SelectTargetEnemy
                    elif self.battle.ui.selected_action == 1:
                        self.battle.ui.menu_state = BattleMenuState.MagicSelect
                        self.magic_selection_menu_init(player_role, True, 0)
                    elif self.battle.ui.selected_action == 2:
                        w = self.party[self.battle.ui.cur_player_index].player_role
                        w = self.get_player_cooperative_magic(w)
                        self.battle.ui.action_type = BattleActionType.CoopMagic
                        self.battle.ui.object_id = w
                        if self.objects[w].magic.flags & MagicFlag.UsableToEnemy:
                            if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                                self.battle.ui.state = BattleUIState.SelectTargetEnemyAll
                            else:
                                if self.battle.ui.prev_enemy_target != -1:
                                    self.battle.ui.selected_index = self.battle.ui.prev_enemy_target
                                self.battle.ui.state = BattleUIState.SelectTargetEnemy
                        else:
                            if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                                self.battle.ui.state = BattleUIState.SelectTargetPlayerAll
                            else:
                                self.battle.ui.selected_index = 0
                                self.battle.ui.state = BattleUIState.SelectTargetPlayer
                    elif self.battle.ui.selected_action == 3:
                        self.battle.ui.menu_state = BattleMenuState.Misc
                        self.cur_misc_menu_item = 0
                elif self.input_state.key_press & Key.Defend:
                    self.battle.ui.action_type = BattleActionType.Defend
                    self.battle_commit_action(False)
                elif self.input_state.key_press & Key.Force:
                    player_role = self.party[self.battle.ui.cur_player_index].player_role
                    w = self.battle_ui_pick_up_auto_magic(player_role, 60)
                    if w == 0:        
                        self.battle.ui.action_type = BattleActionType.Attack
                        if self.player_can_attack_all(player_role):
                            self.battle.ui.selected_index = -1
                        else:
                            self.battle.ui.selected_index = self.battle_select_auto_target()
                    else:    
                        self.battle.ui.action_type = BattleActionType.Magic
                        self.battle.ui.object_id = w
                        if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                            self.battle.ui.selected_index = -1
                        else:
                            self.battle.ui.selected_index = self.battle_select_auto_target()
                    self.battle_commit_action(False)
                elif self.input_state.key_press & Key.Flee:
                    self.battle.ui.action_type = BattleActionType.Flee
                    self.battle_commit_action(False)
                elif self.input_state.key_press & Key.UseItem:
                    self.battle.ui.menu_state = BattleMenuState.UseItemSelect
                    self.item_select_menu_init(ItemFlag.Usable)
                elif self.input_state.key_press & Key.ThrowItem:
                    self.battle.ui.menu_state = BattleMenuState.ThrowItemSelect
                    self.item_select_menu_init(ItemFlag.Throwable)
                elif self.input_state.key_press & Key.Repeat:
                    self.battle_commit_action(True)
                elif self.input_state.key_press & Key.Menu:
                    self.battle.players[self.battle.ui.cur_player_index].state = FighterState.Wait
                    self.battle.ui.state = BattleUIState.Wait
                    if self.battle.ui.cur_player_index > 0:
                        f = True
                        while f:
                            self.battle.ui.cur_player_index -= 1
                            self.battle.players[self.battle.ui.cur_player_index].state = FighterState.Wait
                            if self.battle.players[self.battle.ui.cur_player_index].action.action_type == BattleActionType.ThrowItem:
                                for i in range(MAX_INVENTORY):
                                    if self.inventory[i].item == self.battle.players[self.battle.ui.cur_player_index].action.action_id:
                                        self.inventory[i].amount_in_use -= 1
                                        break
                            elif self.battle.players[self.battle.ui.cur_player_index].action.action_type == BattleActionType.UseItem:
                                if self.objects[self.battle.players[self.battle.ui.cur_player_index].action.action_id].item.flags & ItemFlag.Consuming:
                                    for i in range(MAX_INVENTORY):
                                        if self.inventory[i].item == self.battle.players[self.battle.ui.cur_player_index].action.action_id:
                                            self.inventory[i].amount_in_use -= 1
                                            break
                            player_role = self.party[self.battle.ui.cur_player_index].player_role
                            f = (
                                    self.battle.ui.cur_player_index > 0 and (
                                    self.player_roles.hp[player_role] == 0 or
                                    self.player_status[player_role][Status.Confused] > 0 or
                                    self.player_status[player_role][Status.Sleep] > 0 or
                                    self.player_status[player_role][Status.Paralyzed] > 0
                                )
                            )
            elif self.battle.ui.menu_state == BattleMenuState.MagicSelect:
                w = self.magic_selection_menu_update()
                if w != 0xFFFF:
                    self.battle.ui.menu_state = BattleMenuState.Main
                    if w != 0:
                        self.battle.ui.action_type = BattleActionType.Magic
                        self.battle.ui.object_id = w
                        if self.objects[w].magic.flags & MagicFlag.UsableToEnemy:
                            if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                                self.battle.ui.state = BattleUIState.SelectTargetEnemyAll
                            else:
                                if self.battle.ui.prev_enemy_target != -1:
                                    self.battle.ui.selected_index = self.battle.ui.prev_enemy_target
                                self.battle.ui.state = BattleUIState.SelectTargetEnemy
                        else:
                            if self.objects[w].magic.flags & MagicFlag.ApplyToAll:
                                self.battle.ui.state = BattleUIState.SelectTargetPlayerAll
                            else:
                                self.battle.ui.selected_index = 0
                                self.battle.ui.state = BattleUIState.SelectTargetPlayer
            elif self.battle.ui.menu_state == BattleMenuState.UseItemSelect:
                self.battle_ui_use_item()
            elif self.battle.ui.menu_state == BattleMenuState.ThrowItemSelect:
                self.battle_ui_throw_item()
            elif self.battle.ui.menu_state == BattleMenuState.Misc:
                w = self.battle_ui_misc_menu_update()
                if w != 0xFFFF:
                    self.battle.ui.menu_state = BattleMenuState.Main
                    if w == 2:
                        self.battle.ui.menu_state = BattleMenuState.MiscItemSubMenu
                        self.cur_sub_menu_item = 0
                    elif w == 3:
                        self.battle.ui.action_type = BattleActionType.Defend
                        self.battle_commit_action(False)
                    elif w == 1:
                        self.battle.ui.auto_attack = True
                    elif w == 4:
                        self.battle.ui.action_type = BattleActionType.Flee
                        self.battle_commit_action(False)
                    elif w == 5:
                        self.show_player_status()
            elif self.battle.ui.menu_state == BattleMenuState.MiscItemSubMenu:
                w = self.battle_ui_misc_item_sub_menu_update()
                if w != 0xFFFF:
                    self.battle.ui.menu_state = BattleMenuState.Main
                    if w == 1:
                        self.battle.ui.menu_state = BattleMenuState.UseItemSelect
                        self.item_select_menu_init(ItemFlag.Usable)
                    elif w == 2:
                        self.battle.ui.menu_state = BattleMenuState.ThrowItemSelect
                        self.item_select_menu_init(ItemFlag.Throwable)
        elif self.battle.ui.state == BattleUIState.SelectTargetEnemy:
            x = -1
            y = 0
            for i in range(self.battle.max_enemy_index + 1):
                if self.battle.enemies[i].object_id != 0:
                    x = i
                    y += 1
            if x == -1:
                self.battle.ui.state = BattleUIState.SelectMove
                return self.battle_ui_update_end()
            if self.battle.ui.action_type == BattleActionType.CoopMagic:
                if not self.battle_ui_is_action_valid(BattleActionType.CoopMagic):
                    self.battle.ui.state = BattleUIState.SelectMove
                    return self.battle_ui_update_end()
            if y == 1:
                self.battle.ui.prev_enemy_target = x
                if self.battle.ui.selected_index == -1:
                    self.battle.ui.selected_index = x
                self.battle_commit_action(False)
                return self.battle_ui_update_end()
            if self.battle.ui.selected_index > x:
                self.battle.ui.selected_index = x
            for i in range(x):
                if self.battle.enemies[self.battle.ui.selected_index].object_id != 0:
                    break
                self.battle.ui.selected_index += 1
                self.battle.ui.selected_index %= x + 1
            if save['frame'] & 1:
                i = self.battle.ui.selected_index
                ex, ey = self.battle.enemies[i].pos
                ex -= self.battle.enemies[i].sprite[self.battle.enemies[i].current_frame].width // 2
                ey -= self.battle.enemies[i].sprite[self.battle.enemies[i].current_frame].height
                self.battle.enemies[i].sprite[self.battle.enemies[i].current_frame].blit_with_color_shift(
                    self.screen, (ex, ey), 7
                )
            if self.input_state.key_press & Key.Menu:
                self.battle.ui.state = BattleUIState.SelectMove
            elif self.input_state.key_press & Key.Search:
                self.battle.ui.prev_enemy_target = self.battle.ui.selected_index
                self.battle_commit_action(False)
            elif self.input_state.key_press & (Key.Left | Key.Down):
                self.battle.ui.selected_index -= 1
                if self.battle.ui.selected_index < 0:
                    self.battle.ui.selected_index = MAX_ENEMIES_IN_TEAM - 1
                while (
                    self.battle.ui.selected_index != 0 and
                    self.battle.enemies[self.battle.ui.selected_index].object_id == 0
                ):
                    self.battle.ui.selected_index -= 1
                    if self.battle.ui.selected_index < 0:
                        self.battle.ui.selected_index = MAX_ENEMIES_IN_TEAM - 1
            elif self.input_state.key_press & (Key.Right | Key.Up):
                self.battle.ui.selected_index += 1
                if self.battle.ui.selected_index >= MAX_ENEMIES_IN_TEAM:
                    self.battle.ui.selected_index = 0
                while (
                    self.battle.ui.selected_index < MAX_ENEMIES_IN_TEAM and
                    self.battle.enemies[self.battle.ui.selected_index].object_id == 0
                ):
                    self.battle.ui.selected_index += 1
                    if self.battle.ui.selected_index >= MAX_ENEMIES_IN_TEAM:
                        self.battle.ui.selected_index = 0
        elif self.battle.ui.state == BattleUIState.SelectTargetPlayer:
            if self.max_party_member_index == 0:
                self.battle.ui.selected_index = 0
                self.battle_commit_action(False)
            j = SPRITENUM_BATTLE_ARROW_SELECTEDPLAYER
            if save['frame'] & 1:
                j = SPRITENUM_BATTLE_ARROW_SELECTEDPLAYER_RED
            x = pal_x(player_pos[self.max_party_member_index][self.battle.ui.selected_index]) - 8
            y = pal_y(player_pos[self.max_party_member_index][self.battle.ui.selected_index]) - 67
            self.sprite_ui[j].blit_to(self.screen, (x, y))
            if self.input_state.key_press & Key.Menu:
                self.battle.ui.state = BattleUIState.SelectMove
            elif self.input_state.key_press & Key.Search:
                self.battle_commit_action(False)
            elif self.input_state.key_press & (Key.Left | Key.Down):
                if self.battle.ui.selected_index != 0:
                    self.battle.ui.selected_index -= 1
                else:
                    self.battle.ui.selected_index = self.max_party_member_index
            elif self.input_state.key_press & (Key.Right | Key.Up):
                if self.battle.ui.selected_index < self.max_party_member_index:
                    self.battle.ui.selected_index += 1
                else:
                    self.battle.ui.selected_index = 0
        elif self.battle.ui.state in {
            BattleUIState.SelectTargetEnemyAll,
            BattleUIState.SelectTargetPlayerAll
        }:
            self.battle.ui.selected_index = -1
            self.battle_commit_action(False)
        return self.battle_ui_update_end()

    def battle_ui_draw_misc_menu(self, current_item, confirmed):
        menu_items = [
            MenuItem(
                i, self.words[label], True, (16, 32 + i * 18)
            )
            for i, label in enumerate([
                BATTLEUI_LABEL_AUTO,
                BATTLEUI_LABEL_INVENTORY,
                BATTLEUI_LABEL_DEFEND,
                BATTLEUI_LABEL_FLEE,
                BATTLEUI_LABEL_STATUS
            ])
        ]
        self.create_box(
            (2, 20), 4, self.menu_text_max_width(menu_items) - 1,
            0, False
        )
        for i, item in enumerate(menu_items):
            color = MENUITEM_COLOR
            if i == current_item:
                if confirmed:
                    color = MENUITEM_COLOR_CONFIRMED
                else:
                    color = menuitem_color_selected()
            self.draw_text(
                item.label, item.pos,
                color, True, False
            )

    def battle_ui_misc_menu_update(self):
        self.battle_ui_draw_misc_menu(self.cur_misc_menu_item, False)
        if self.input_state.key_press & (Key.Up | Key.Left):
            self.cur_misc_menu_item -= 1
            if self.cur_misc_menu_item < 0:
                self.cur_misc_menu_item = 4
        elif self.input_state.key_press & (Key.Down | Key.Right):
            self.cur_misc_menu_item += 1
            if self.cur_misc_menu_item > 4:
                self.cur_misc_menu_item = 0
        elif self.input_state.key_press & Key.Search:
            return self.cur_misc_menu_item + 1
        elif self.input_state.key_press & Key.Menu:
            return 0
        return 0xFFFF

    def battle_ui_misc_item_sub_menu_update(self):
        menu_items = [
            MenuItem(
                0, self.words[BATTLEUI_LABEL_USEITEM],
                True, (44, 62)
            ),
            MenuItem(
                1, self.words[BATTLEUI_LABEL_THROWITEM],
                True, (44, 80)
            )
        ]
        self.battle_ui_draw_misc_menu(0, True)
        self.create_box(
            (30, 50), 1, self.menu_text_max_width(menu_items) - 1,
            0, False
        )
        for i, item in enumerate(menu_items):
            color = MENUITEM_COLOR
            if i == self.cur_sub_menu_item:
                color = menuitem_color_selected()
            self.draw_text(
                item.label, item.pos,
                color, True, False
            )
        if self.input_state.key_press & (Key.Up | Key.Left):
            self.cur_sub_menu_item = 0
        elif self.input_state.key_press & (Key.Down | Key.Right):
            self.cur_sub_menu_item = 1
        elif self.input_state.key_press & Key.Search:
            return self.cur_sub_menu_item + 1
        elif self.input_state.key_press & Key.Menu:
            return 0
        return 0xFFFF

    def battle_ui_show_text(self, text, duration):
        if not pg.time.get_ticks() >= self.battle.ui.msg_show_time:
            self.battle.ui.next_msg = text
            self.batle.ui.next_msg_duration = duration
        else:
            self.battle.ui.msg = text
            self.battle.ui.msg_show_time = pg.time.get_ticks() + duration

    def battle_ui_show_num(self, num, pos, color):
        for i in range(BATTLEUI_MAX_SHOWNUM):
            if self.battle.ui.show_nums[i].num == 0:
                self.battle.ui.show_nums[i].num = num
                self.battle.ui.show_nums[i].pos = (pal_x(pos) - 15, pal_y(pos))
                self.battle.ui.show_nums[i].color = color
                self.battle.ui.show_nums[i].time = pg.time.get_ticks()
                break

    def battle_ui_use_item(self):
        selected_item = self.item_select_menu_update()
        if selected_item != 0xFFFF:
            if selected_item != 0:
                self.battle.ui.action_type = BattleActionType.UseItem
                self.battle.ui.object_id = selected_item
                if self.objects[selected_item].item.flags & ItemFlag.ApplyToAll:
                    self.battle.ui.state = BattleUIState.SelectTargetPlayerAll
                else:
                    self.battle.ui.selected_index = 0
                    self.battle.ui.state = BattleUIState.SelectTargetPlayer
            else:
                self.battle.ui.menu_state = BattleMenuState.Main

    def battle_ui_throw_item(self):
        selected_item = self.item_select_menu_update()
        if selected_item != 0xFFFF:
            if selected_item != 0:
                self.battle.ui.action_type = BattleActionType.ThrowItem
                self.battle.ui.object_id = selected_item
                if self.objects[selected_item].item.flags & ItemFlag.ApplyToAll:
                    self.battle.ui.state = BattleUIState.SelectTargetEnemyAll
                else:
                    if self.battle.ui.prev_enemy_target != -1:
                        self.battle.ui.selected_index = self.battle.ui.prev_enemy_target
                    self.battle.ui.state = BattleUIState.SelectTargetEnemy
            else:
                self.battle.ui.menu_state = BattleMenuState.Main

    def battle_ui_player_ready(self, player_index):
        self.battle.ui.cur_player_index = player_index
        self.battle.ui.state = BattleUIState.SelectMove
        self.battle.ui.selected_action = 0
        self.battle.ui.menu_state = BattleMenuState.Main

    def battle_ui_is_action_valid(self, action_type):
        player_role = self.party[self.battle.ui.cur_player_index].player_role
        if action_type == BattleUIAction.Magic:
            if self.player_status[player_role][Status.Silence] != 0:
                return False
        elif action_type == BattleUIAction.CoopMagic:
            if self.max_party_member_index == 0:
                return False
            for i in range(self.max_party_member_index + 1):
                w = self.party[i].player_role
                if (
                    self.player_roles.hp[w] < self.player_roles.max_hp[w] // 5 or
                    self.player_status[w][Status.Sleep] != 0 or
                    self.player_status[w][Status.Confused] != 0 or
                    self.player_status[w][Status.Silence] != 0
                ):
                    return False
        return True

    def battle_ui_pick_up_auto_magic(self, player_role, random_range):
        magic = 0
        max_power = 0
        if self.player_status[player_role][Status.Silence] != 0:
            return 0
        for i in range(MAX_PLAYER_MAGICS):
            w = self.player_roles.magic[i][player_role]
            if w == 0:
                continue
            magic_num = self.objects[w].magic.magic_number
            if (
                self.magics[magic_num].cost_mp == 1 or
                self.magics[magic_num].cost_mp > self.player_roles.mp[player_role] or
                self.magics[magic_num].base_damage <= 0
            ):
                continue
            power = self.magics[magic_num].base_damage + random.randint(0, random_range)
            if power > max_power:
                max_power = power
                magic = w
        return magic

    def player_info_box(self, pos, player_role, update):
        self.sprite_ui[SPRITENUM_PLAYERINFOBOX].blit_to(self.screen, pos)
        max_level = 0
        poison_color = 0xFF
        party_index = 0
        while party_index <= self.max_party_member_index:
            if self.party[party_index].player_role == player_role:
                break
            party_index += 1
        if party_index <= self.max_party_member_index:
            for i in range(MAX_POISONS):
                w = self.poison_status[i][party_index].poison_id
                if w != 0 and self.objects[w].poison.poison_level <= 3:
                    if self.objects[w].poison.poison_level >= max_level:
                        max_level = self.objects[w].poison.poison_level
                        poison_color = byte(self.objects[w].poison.color)
        if self.player_roles.hp[player_role] == 0:
            poison_color = 0
        if poison_color == 0xFF:
            self.sprite_ui[SPRITENUM_PLAYERFACE_FIRST + player_role].blit_to(
                self.screen, (pal_x(pos) - 2, pal_y(pos) - 4)
            )
        else:
            self.sprite_ui[SPRITENUM_PLAYERFACE_FIRST + player_role].blit_mono_color(
                self.screen, (pal_x(pos) - 2, pal_y(pos) - 4),
                0, poison_color
            )
        self.sprite_ui[SPRITENUM_SLASH].blit_to(self.screen, (pal_x(pos) + 49, pal_y(pos) + 6))
        self.draw_number(
            self.player_roles.max_hp[player_role], 4,
            (pal_x(pos) + 47, pal_y(pos) + 8),
            NumColor.Yellow, NumAlign.Right
        )
        self.draw_number(
            self.player_roles.hp[player_role], 4,
            (pal_x(pos) + 26, pal_y(pos) + 5),
            NumColor.Yellow, NumAlign.Right
        )
        self.sprite_ui[SPRITENUM_SLASH].blit_to(self.screen, (pal_x(pos) + 49, pal_y(pos) + 22))
        self.draw_number(
            self.player_roles.max_mp[player_role], 4,
            (pal_x(pos) + 47, pal_y(pos) + 24),
            NumColor.Cyan, NumAlign.Right
        )
        self.draw_number(
            self.player_roles.mp[player_role], 4,
            (pal_x(pos) + 26, pal_y(pos) + 21),
            NumColor.Cyan, NumAlign.Right
        )
        if self.player_roles.hp[player_role] > 0:
            for i in range(Status.All):
                if self.player_status[player_role][i] > 0 and Status(i).word != 0:
                    self.draw_text(
                        self.words[Status(i).word],
                        (
                            pal_x(pos) + pal_x(Status(i).pos),
                            pal_y(pos) + pal_y(Status(i).pos)
                        ),
                        Status(i).color, True, False
                    )
        if update:
            rect = pg.Rect(
                pal_x(pos) - 2,
                pal_y(pos) - 4,
                77, 39
            )
            self.update_screen(rect)
