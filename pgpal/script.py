#! /usr/bin/env python
# -*- coding: utf-8 -*-
from functools import partial
import random
from struct import pack_into, unpack_from
from pgpal.battle import BattleEnemy
from pgpal.compat import pg, range
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.player import Players
from pgpal.saves import PoisonStatusTable
from pgpal.utils import pal_x, pal_y, pal_h, short, byte, static_vars, RunResult


class InterpreterContext(object):

    def __init__(self, game, script_entry, event_object_id):
        self.script_entry = script_entry
        self.event_object_id = event_object_id
        self.game = game
        script = self.game.scripts[script_entry]
        if script.p1 in {0x00, 0xFFFF}:
            self.current = self.evt_obj
            self.cur_event_object_id = event_object_id
        else:
            i = script.p1 - 1
            if i > 0x9000:
                i -= 0x9000
            if i < len(self.game.event_objects):
                self.current = self.game.event_objects[i]
            else:
                self.current = None
            self.cur_event_object_id = script.p1
        role_index = script.p1 if script.p1 < MAX_PLAYABLE_PLAYER_ROLES else 0
        self.player_role = self.game.party[role_index].player_role

        if script.op in self.commands:
            self.commands[script.op](
                self, *script.params
            )
        else:
            raise Exception(
                'SCRIPT: Invalid Instruction at %4x: %4x - %4x, %4x, %4x'.format(
                    self.script_entry, script.op, *script.params
                )
            )

    @property
    def evt_obj(self):
        return self.game.event_objects[self.event_object_id - 1]

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        del self.game
        del self.current

    def walk_one_step(self, *args, **kwargs):
        self.evt_obj.direction = kwargs['op'] - 0x0B
        self.game.npc_walk_one_step(self.event_object_id, 2)

    set_south_dir = partial(walk_one_step, op=0x0B)
    set_west_dir = partial(walk_one_step, op=0x0C)
    set_north_dir = partial(walk_one_step, op=0x0D)
    set_east_dir = partial(walk_one_step, op=0x0E)

    def set_npc_dir(self, *args):
        if args[0] != 0xFFFF:
            self.evt_obj.direction = args[0]
        if args[1] != 0xFFFF:
            self.evt_obj.current_frame_num = args[1]

    def npc_walk(self, *args):
        if not self.game.npc_walk_to(
            self.event_object_id,
            args[0], args[1], args[2], 3
        ):
            self.script_entry -= 1

    def npc_walk_slow(self, *args):
        if (self.event_object_id & 1) ^ (self.game.frame_num & 1):
            if not self.game.npc_walk_to(
                self.event_object_id,
                args[0], args[1], args[2], 2
            ):
                self.script_entry -= 1
        else:
            self.script_entry -= 1

    def set_npc_rel_pos(self, *args):
        self.current.x = short(args[1]) + \
                         pal_x(self.game.viewport) + pal_x(self.game.partyoffset)
        self.current.y = short(args[2]) + \
                         pal_y(self.game.viewport) + pal_y(self.game.partyoffset)

    def set_npc_pos(self, *args):
        self.current.x = args[1]
        self.current.y = args[2]

    def set_npc_frame(self, *args):
        self.evt_obj.current_frame_num = args[0]
        self.evt_obj.direction = Direction.South

    def set_role_dir_frame(self, *args):
        self.game.party_direction = args[0]
        self.game.party[args[2]].frame = self.game.party_direction * 3 + args[1]

    def set_npc_dir_frame(self, *args):
        if args[0] != 0:
            self.current.direction = args[1]
            self.current.current_frame_num = args[2]

    def set_extra_attr(self, *args):
        i = args[0] - 0xB
        p = self.game.equipment_effect[i]
        offset = args[1] * Players.struct_size + self.event_object_id * 2
        pack_into('h', p._buffer, offset, short(args[2]))
        p.__init__(p._buffer)

    def equip_item(self, *args):
        i = args[0] - 0x0B
        self.game.cur_equip_part = i
        self.game.remove_equipment_effect(self.event_object_id, i)
        if self.game.player_roles.equipment[i][self.event_object_id] != args[1]:
            w = self.game.player_roles.equipment[i][self.event_object_id]
            self.game.player_roles.equipment[i][self.event_object_id] = args[1]
            self.game.add_item_to_inventory(args[1], -1)
            if w != 0:
                self.game.add_item_to_inventory(w, 1)
            self.game.last_unequipped_item = w

    def adjust_player_attr(self, *args):
        p = self.game.player_roles
        if args[2] == 0:
            player_role = self.event_object_id
        else:
            player_role = args[2] - 1
        offset = args[0] * Players.struct_size + player_role * 2
        ori = unpack_from('H', p._buffer[offset: offset+2])[0]
        pack_into('H', p._buffer, offset, (ori + short(args[1])) & 0xFFFF)
        p.__init__(p._buffer)

    def set_player_stat(self, *args):
        if self.game.cur_equip_part != -1:
            p = self.game.equipment_effect[self.game.cur_equip_part]
        else:
            p = self.game.player_roles
        if args[2] == 0:
            player_role = self.event_object_id
        else:
            player_role = args[2] - 1
        offset = args[0] * Players.struct_size + player_role * 2
        pack_into('h', p._buffer, offset, short(args[1]))
        p.__init__(p._buffer)

    def adjust_hp(self, *args):
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                self.game.increase_hp_mp(w, short(args[1]), 0)
        else:
            if not self.game.increase_hp_mp(self.event_object_id, short(args[1]), 0):
                self.mark_failed_script()

    def adjust_mp(self, *args):
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                self.game.increase_hp_mp(w, 0, short(args[1]))
        else:
            if not self.game.increase_hp_mp(self.event_object_id, 0, short(args[1])):
                self.mark_failed_script()

    def adjust_hp_mp(self, *args):
        diff = short(args[1])
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                self.game.increase_hp_mp(w, diff, diff)
        else:
            if not self.game.increase_hp_mp(self.event_object_id, diff, diff):
                self.mark_failed_script()

    def set_money(self, *args):
        diff = short(args[0])
        if diff < 0 and self.game.cash < abs(diff):
            self.script_entry = args[1] - 1
        else:
            self.game.cash += diff

    def add_inventory(self, *args):
        self.game.add_item_to_inventory(
            args[0], short(args[1])
        )

    def remove_inventory(self, *args):
        if not self.game.add_item_to_inventory(args[0], -(args[1] or 1)):
            x = args[1] or 1
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                for j in range(MAX_PLAYER_EQUIPMENTS):
                    if self.game.player_roles.equipment[j][w] == args[0]:
                        self.game.remove_equipment_effect(w, j)
                        self.game.player_roles.equipment[j][w] = 0
                        x -= 1
                        if x == 0:
                            i = 9999
                            break
            if x > 0 and args[2] != 0:
                self.script_entry = args[2] - 1

    def inflict_damage(self, *args):
        if args[0]:
            for i in range(self.game.battle.max_enemy_index + 1):
                if self.game.battle.enemies[i].e.health != 0:
                    self.game.battle.enemies[i].e.health -= self.game.battle.enemies[i].e.health
        else:
            self.game.battle.enemies[self.event_object_id].e.health -= args[1]

    def revive_player(self, *args):
        if args[0]:
            self.mark_failed_script()
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                if self.game.player_roles.hp[w] == 0:
                    self.game.player_roles.hp[w] = self.game.player_roles.max_hp[w] * args[1] // 10
                    self.game.cure_poison_by_level(w, 3)
                    for x in range(Status.All):
                        self.game.remove_player_status(w, x)
                    RunResult.success = True
        else:
            if self.game.player_roles.hp[self.event_object_id] == 0:
                w = self.event_object_id
                self.game.player_roles.hp[w] = self.game.player_roles.max_hp[w] * args[1] // 10
                self.game.cure_poison_by_level(w, 3)
                for x in range(Status.All):
                    self.game.remove_player_status(w, x)
            else:
                self.mark_failed_script()

    def remove_equip(self, *args):
        if args[1] == 0:
            for i in range(MAX_PLAYER_EQUIPMENTS):
                w = self.game.player_roles.equipment[i][self.player_role]
                if w != 0:
                    self.game.add_item_to_inventory(w, 1)
                    self.game.player_roles.equipment[i][self.player_role] = 0
                self.game.remove_equipment_effect(self.player_role, i)
        else:
            i = args[1] - 1
            w = self.game.player_roles.equipment[i][self.player_role]
            if w != 0:
                self.game.remove_equipment_effect(self.player_role, i)
                self.game.add_item_to_inventory(w, 1)
                self.game.player_roles.equipment[i][self.player_role] = 0

    def set_npc_auto_script(self, *args):
        if args[0] != 0:
            self.current.auto_script = args[1]

    def set_npc_trigger_script(self, *args):
        if args[0] != 0:
            self.current.trigger_script = args[1]

    def menu_buy(self, *args):
        self.game.make_scene()
        self.game.update_screen()
        self.game.buy_menu(args[0])

    def menu_sell(self, *args):
        self.game.make_scene()
        self.game.update_screen()
        self.game.sell_menu()

    def poison_enemy(self, *args):
        if args[0]:
            targets = range(self.game.battle.max_enemy_index + 1)
        else:
            targets = [self.event_object_id]
        for i in targets:
            w = self.game.battle.enemies[i].object_id
            if w == 0:
                continue
            if random.randint(0, 9) >= self.game.objects[w].enemy.resistance_to_sorcery:
                j = 0
                while j < MAX_POISONS:
                    if self.game.battle.enemies[i].poisons[j].poison_id == args[1]:
                        break
                    j += 1
                if j >= MAX_POISONS:
                    for j in range(MAX_POISONS):
                        if self.game.battle.enemies[self.event_object_id].poisons[j].poison_id == 0:
                            self.game.battle.enemies[self.event_object_id].poisons[j].poison_id = args[1]
                            self.game.battle.enemies[self.event_object_id].poisons[j].poison_script = self.game.run_trigger_script(
                                self.game.objects[args[1]].poison.enemy_script, self.event_object_id
                            )
                            break

    def poison_player(self, *args):
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                if random.randint(1, 100) > self.game.get_player_poison_resistance(w):
                    self.game.add_poison_for_player(w, args[1])
        elif random.randint(1, 100) > self.game.get_player_poison_resistance(self.event_object_id):
            self.game.add_poison_for_player(self.event_object_id, args[1])

    def cure_enemy(self, *args):
        if args[0]:
            targets = range(self.game.battle.max_enemy_index + 1)
        else:
            targets = [self.event_object_id]
        for i in targets:
            if self.game.battle.enemies[i].object_id == 0:
                continue
            for j in range(MAX_POISONS):
                if self.game.battle.enemies[i].poisons[j].poison_id == args[1]:
                    self.game.battle.enemies[i].poisons[j].poison_id = 0
                    self.game.battle.enemies[i].poisons[j].poison_script = 0
                    break

    def cure_by_kind(self, *args):
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                self.game.cure_poison_by_kind(w, args[1])
        else:
            self.game.cure_poison_by_kind(self.event_object_id, args[1])

    def cure_by_level(self, *args):
        if args[0]:
            for i in range(self.game.max_party_member_index + 1):
                w = self.game.party[i].player_role
                self.game.cure_poison_by_level(w, args[1])
        else:
            self.game.cure_poison_by_level(self.event_object_id, args[1])

    def set_player_status(self, *args):
        self.game.set_player_status(self.event_object_id, args[0], args[1])

    def set_enemy_status(self, *args):
        w = self.game.battle.enemies[self.event_object_id].object_id
        i = 9
        if (
            random.randint(0, i) >= self.game.objects[w].enemy.resistance_to_sorcery and
            self.game.battle.enemies[self.event_object_id].status[args[0]] == 0
        ):
            self.game.battle.enemies[self.event_object_id].status[args[0]] = args[1]
        else:
            self.script_entry = args[2] - 1

    def remove_player_status(self, *args):
        self.game.remove_player_status(self.event_object_id, args[0])

    def inc_stat_temp(self, *args):
        p = self.game.equipment_effect[BodyPart.Extra]
        if args[2] == 0:
            player_role = self.event_object_id
        else:
            player_role = args[2] - 1
        offset = (args[0] * MAX_PLAYER_ROLES + player_role) * 2
        pack_into(
            'H', p._buffer, offset,
            (unpack_from(
                'H', self.game.player_roles._buffer, offset
            )[0] * short(args[1]) // 100) & 0xFFFF
        )
        p.__init__(p._buffer)

    def change_sprite_temp(self, *args):
        self.game.equipment_effect[BodyPart.Extra].sprite_num_in_battle[
            self.event_object_id
        ] = args[0]

    def collect_enemy_items(self, *args):
        if self.game.battle.enemies[self.event_object_id].e.collect_value != 0:
            self.game.collect_value = self.game.battle.enemies[self.event_object_id].e.collect_value
        else:
            self.script_entry = args[0] - 1

    @static_vars(prev_image_index=0xFFFF, buf_image=None)
    def trans_enemy_items(self, *args):
        save = self.trans_enemy_items.__dict__
        if self.game.collect_value > 0:
            i = min(random.randint(1, self.game.collect_value), 9)
            self.game.collect_value -= i
            i -= 1
            self.game.add_item_to_inventory(self.game.store[0][i], 1)
            self.game.dialog_shadow = 5
            self.game.start_dialog_with_offset(
                DialogPos.CenterWindow, 0, 0, False, 0, -10
            )
            bg = self.game.sprite_ui[SPRITENUM_ITEMBOX]
            pos = (
                (320 - bg.width) // 2,
                (200 - bg.height) // 2
            )
            rect = pg.Rect(pos, bg.size)
            bg.blit_to(self.game.screen, pos)

            obj = self.game.store[0][i]
            if self.game.objects[obj].item.bitmap != save['prev_image_index']:
                save['buf_image'] = self.game.ball[self.game.objects[obj].item.bitmap]
                if save['buf_image'] is not None:
                    save['prev_image_index'] = self.game.objects[obj].item.bitmap
                else:
                    save['prev_image_index'] = 0xFFFF
            if save['prev_image_index'] != 0xFFFF:
                save['buf_image'].blit_to(
                    self.game.screen,
                    (
                        pal_x(pos) + 8,
                        pal_y(pos) + 7
                    )
                )

            self.game.update_screen(rect)
            self.game.show_dialog_text(
                self.game.words[42] + self.game.words[obj]
            )
            self.game.dialog_shadow = 0
        else:
            self.script_entry = args[0] - 1

    def shake_screen(self, *args):
        self.game.shake_time = args[0]
        self.game.shake_level = args[1] or 4
        if not args[0]:
            self.game.update_screen()

    def set_rng(self, *args):
        self.game.cur_playing_rng = args[0]

    def play_rng(self, *args):
        self.game.play_rng(
            self.game.cur_playing_rng,
            args[0],
            args[1] or 999,
            args[2] or 16
        )

    def teleport_party(self, *args):
        if (
            not self.game.in_battle and
            self.game.scenes[self.game.num_scene - 1].script_on_teleport != 0
        ):
            self.game.run_trigger_script(
                self.game.scenes[self.game.num_scene - 1].script_on_teleport,
                0xFFFF
            )
        else:
            self.mark_failed_script()
            self.script_entry = args[0] - 1

    def drain_hp(self, *args):
        w = self.game.party[self.game.battle.moving_player_index].player_role
        self.game.battle.enemies[self.event_object_id].e.health -= args[0]
        self.game.player_roles.hp[w] += args[0]
        if self.game.player_roles.hp[w] > self.game.player_roles.max_hp[w]:
            self.game.player_roles.hp[w] = self.game.player_roles.max_hp[w]

    def flee_from_battle(self, *args):
        if self.game.battle.is_boss:
            self.script_entry = args[0] - 1
        else:
            self.game.battle_player_escape()

    def ride_event_object_slow(self, *args):
        self.game.party_ride_event_object(
            self.event_object_id,
            args[0], args[1], args[2], 2
        )

    def set_trigger_mode(self, *args):
        if args[0] != 0:
            self.current.trigger_mode = args[1]

    def mark_failed_script(self, *args):
        RunResult.success = False

    def simulate_magic(self, *args):
        i = short(args[2]) - 1
        if i < 0:
            i = self.event_object_id
        self.game.battle_simulate_magic(i, args[0], args[1])

    def play_music(self, *args):
        self.game.num_music = args[0]
        self.game.play_music(args[0], args[0] != 0x3D, args[1])

    def ride_event_object_norm(self, *args):
        self.game.party_ride_event_object(
            self.event_object_id,
            args[0], args[1], args[2], 4
        )

    def set_battle_music(self, *args):
        self.game.num_battle_music = args[0]

    def set_party_pos(self, *args):
        x_offset = 16 if self.game.party_direction in {Direction.West, Direction.South} else -16
        y_offset = 8 if self.game.party_direction in {Direction.West, Direction.North} else -8
        x = pal_x(args) * 32 + pal_h(args) * 16
        y = pal_y(args) * 16 + pal_h(args) * 8
        x -= pal_x(self.game.partyoffset)
        y -= pal_y(self.game.partyoffset)
        self.game.viewport = x, y
        x, y = self.game.partyoffset
        for i in range(MAX_PLAYABLE_PLAYER_ROLES):
            self.game.party[i].x = x
            self.game.party[i].y = y
            self.game.trail[i].x = max(short(x + pal_x(self.game.viewport)), 0)
            self.game.trail[i].y = max(short(y + pal_y(self.game.viewport)), 0)
            self.game.trail[i].direction = self.game.party_direction
            x += x_offset
            y += y_offset

    def play_sound(self, *args):
        self.game.play_sound(args[0])

    def set_npc_state(self, *args):
        self.current.state = args[1]

    def set_battle_field(self, *args):
        self.game.num_battle_field = args[0]

    def nullify_npc_a_while(self, *args):
        self.evt_obj.vanish_time = 15

    def monster_chase_player(self, *args):
        i, j = args[:2]
        if i == 0:
            i = 8
        if j == 0:
            j = 4
        self.game.monster_chase_player(self.event_object_id, j, i, args[2])

    def wait_for_key(self, *args):
        self.game.wait_for_key(0)

    def load_last_save(self, *args):
        self.game.fadeout(1)
        self.game.init_game_data(self.game.cur_save_slot)

    def fade_to_red(self, *args):
        self.game.fade_to_red()

    def fade_out(self, *args):
        self.game.update_screen()
        self.game.fadeout(args[0] or 1)
        self.game.need_fadein = True

    def fade_in(self, *args):
        self.game.update_screen()
        self.game.fadein(args[0] if short(args[0]) > 0 else 1)
        self.game.need_fadein = False

    def hide_npc_a_while(self, *args):
        self.evt_obj.state *= -1
        self.evt_obj.vanish_time = args[0] or 800

    def set_day_palette(self, *args):
        self.game.night_palette = False

    def set_night_palette(self, *args):
        self.game.night_palette = True

    def add_player_magic(self, *args):
        i = args[1]
        if i == 0:
            i = self.event_object_id
        else:
            i -= 1
        self.game.add_magic(i, args[0])

    def remove_player_magic(self, *args):
        i = self.event_object_id if args[1] == 0 else args[1] - 1
        self.game.remove_magic(i, args[0])

    def magic_damage_by_mp(self, *args):
        i = args[1] or 8
        j = self.game.objects[args[0]].magic.magic_number
        self.game.magics[j].base_damage = self.game.player_roles.mp[self.event_object_id] * i
        self.game.player_roles.mp[self.event_object_id] = 0

    def jump_by_item_count(self, *args):
        if self.game.get_item_amount(args[0]) < short(args[1]):
            self.script_entry = args[2] - 1

    def goto_scene(self, *args):
        if 0 < args[0] <= MAX_SCENES and self.game.num_scene != args[0]:
            self.game.num_scene = args[0]
            self.game.load_flags |= LoadResFlag.Scene
            self.game.entering_scene = True
            self.game.layer = 0

    def halve_player_hp(self, *args):
        self.game.player_roles.hp[self.event_object_id] //= 2

    def halve_enemy_hp(self, *args):
        w = self.game.battle.enemies[self.event_object_id].e.health // 2
        if w > args[0]:
            w = args[0]
        self.game.battle.enemies[self.event_object_id].e.health -= w

    def hide_a_while(self, *args):
        self.game.battle.hiding_time = -args[0]

    def jump_if_no_poison_kind(self, *args):
        if not self.game.is_player_poisoned_by_kind(self.event_object_id, args[0]):
            self.script_entry = args[1] - 1

    def jump_if_no_enemy_poison(self, *args):
        i = 0
        while i < MAX_POISONS:
            if self.game.battle.enemies[self.event_object_id].poisons[i].poison_id == args[0]:
                break
        if i >= MAX_POISONS:
            self.script_entry = args[1] - 1

    def seckill_player(self, *args):
        self.game.player_roles.hp[self.event_object_id] = 0

    def seckill_enemy(self, *args):
        self.game.battle.enemies[self.event_object_id].e.health = 0

    def jump_if_no_poison_level(self, *args):
        if not self.game.is_player_poisoned_by_level(self.event_object_id, 1):
            self.script_entry = args[0] - 1

    def pause_chasing(self, *args):
        self.game.chasespeed_change_cycles = args[0]
        self.game.chase_range = 0

    def speedup_chasing(self, *args):
        self.game.chasespeed_change_cycles = args[0]
        self.game.chase_range = 3

    def jump_by_enemy_hp(self, *args):
        i = self.game.objects[self.game.battle.enemies[self.event_object_id].object_id].enemy.enemy_id
        if (
            self.game.battle.enemies[self.event_object_id].e.health * 100 >
            self.game.enemies[i].health * args[0]
        ):
            self.script_entry = args[1] - 1

    def set_player_sprite(self, *args):
        self.game.player_roles.sprite_num[args[0]] = args[1]
        if not self.game.in_battle and args[2]:
            self.game.load_flags |= LoadResFlag.PlayerSprite
            self.game.load_resources()

    def throw_weapon(self, *args):
        w = args[1] * 5
        w += self.game.player_roles.attack_strength[self.game.party[self.game.battle.moving_player_index].player_role]
        self.game.battle_simulate_magic(short(self.event_object_id), args[0], w)

    def enemy_use_magic(self, *args):
        self.game.battle.enemies[self.event_object_id].e.magic = args[0]
        self.game.battle.enemies[self.event_object_id].e.magic_rate = args[1] or 10

    def jump_if_enemy_act(self, *args):
        if self.game.battle.enemy_moving:
            self.script_entry = args[0] - 1

    def enemy_escape(self, *args):
        self.game.battle_enemy_escape()

    def steal_from_enemy(self, *args):
        self.game.battle_steal_from_enemy(self.event_object_id, args[0])

    def blow_away_enemies(self, *args):
        self.game.battle.blow = short(args[0])

    def npc_walk_step(self, *args):
        self.current.x = max(self.current.x + short(args[1]), 0)
        self.current.y = max(self.current.y + short(args[2]), 0)
        self.game.npc_walk_one_step(self.cur_event_object_id, 0)

    def set_scene_script(self, *args):
        if args[0]:
            if args[1]:
                self.game.scenes[args[0] - 1].script_on_enter = args[1]
            if args[2]:
                self.game.scenes[args[0] - 1].script_on_teleport = args[2]
            if args[1] == args[2] == 0:
                self.game.scenes[args[0] - 1].script_on_enter = 0
                self.game.scenes[args[0] - 1].script_on_teleport = 0

    def move_player_one_step(self, *args):
        for i in range(4, 0, -1):
            self.game.trail[i] = self.game.trail[i - 1]
        self.game.trail[0].direction = self.game.party_direction
        self.game.trail[0].x = pal_x(self.game.viewport) + pal_x(self.game.partyoffset)
        self.game.trail[0].y = pal_y(self.game.viewport) + pal_y(self.game.partyoffset)
        self.game.viewport = (
            pal_x(self.game.viewport) + short(args[0]),
            pal_y(self.game.viewport) + short(args[1])
        )
        self.game.layer = args[2] * 8
        if not args[0] == args[1] == 0:
            self.game.update_party_gestures(True)

    def sync_npc_state(self, *args):
        if self.current.state == short(args[1]):
            self.evt_obj.state = short(args[1])

    def group_walk(self, *args):
        self.game.party_walk_to(args[0], args[1], args[2], 2)

    def wave_screen(self, *args):
        self.game.screen_wave = args[0]
        self.game.wave_progression = short(args[1])

    def fade_to_scene(self, *args):
        self.backup_screen()
        self.game.make_scene()
        self.game.fade_screen(args[0])

    def if_lack_hp(self, *args):
        for i in range(self.game.max_party_member_index + 1):
            w = self.game.party[i].player_role
            if self.game.player_roles.hp[w] < self.game.player_roles.max_hp[w]:
                self.script_entry = args[0] - 1
                return

    def set_role_group(self, *args):
        self.game.max_party_member_index = 0
        for i in range(3):
            if args[i] != 0:
                self.game.party[self.game.max_party_member_index].player_role = (
                    args[i] - 1
                )
                self.game.max_party_member_index += 1
        if self.game.max_party_member_index == 0:
            self.game.party[0].player_role = 0
            self.game.max_party_member_index = 1
        self.game.max_party_member_index -= 1
        self.game.load_flags |= LoadResFlag.PlayerSprite
        self.game.load_resources()
        self.game.poison_status = PoisonStatusTable(None)
        self.game.update_equipments()

    def show_fbp(self, *args):
        if is_win95:
            self.game.screen.fill((0, 0, 0))
            self.game.update_screen()
        else:
            self.game.cur_effect_sprite = 0
            self.game.show_fbp(args[0], args[1])

    def stop_music(self, *args):
        self.game.play_music(0, False, 2.0 if args[0] == 0 else args[0] * 2.0)
        self.game.num_music = 0

    def unknown(self, *args):
        pass

    def jump_by_specific_player(self, *args):
        for i in range(self.game.max_party_member_index + 1):
            if self.game.player_roles.name[
                self.game.party[i].player_role
            ] == args[0]:
                self.script_entry = args[1] - 1
                break

    def group_walk_high(self, *args):
        self.game.party_walk_to(args[0], args[1], args[2], 4)

    def group_walk_highest(self, *args):
        self.game.party_walk_to(args[0], args[1], args[2], 8)

    def npc_walk_high(self, *args):
        if (self.event_object_id & 1) ^ (self.game.frame_num & 1):
            if not self.game.npc_walk_to(
                self.event_object_id,
                args[0], args[1], args[2], 4
            ):
                self.script_entry -= 1
        else:
            self.script_entry -= 1

    def npc_move(self, *args):
        self.current.x += short(args[1])
        self.current.y += short(args[2])

    def set_npc_layer(self, *args):
        self.current.layer = short(args[1])

    def move_viewport(self, *args):
        if args[0] == args[1] == 0:
            x = self.game.party[0].x - 160
            y = self.game.party[0].y - 112
            self.game.viewport = (
                pal_x(self.game.viewport) + x,
                pal_y(self.game.viewport) + y
            )
            self.game.partyoffset = 160, 112
            for i in range(self.game.max_party_member_index + 1):
                self.game.party[i].x -= x
                self.game.party[i].y -= y
            if args[2] != 0xFFFF:
                self.game.make_scene()
                self.game.update_screen()
        else:
            i = 0
            x = short(args[0])
            y = short(args[1])
            ticks = pg.time.get_ticks() + FRAME_TIME
            while True:
                if args[2] == 0xFFFF:
                    x, y = self.game.viewport
                    self.game.viewport = (
                        args[0] * 32 - 160,
                        args[1] * 16 - 112
                    )
                    x -= pal_x(self.game.viewport)
                    y -= pal_y(self.game.viewport)
                    for j in range(self.game.max_party_member_index + 1):
                        self.game.party[j].x += x
                        self.game.party[j].y += y
                else:
                    self.game.viewport = (
                        pal_x(self.game.viewport) + x,
                        pal_y(self.game.viewport) + y
                    )
                    self.game.partyoffset = (
                        pal_x(self.game.partyoffset) - x,
                        pal_y(self.game.partyoffset) - y
                    )
                    for j in range(self.game.max_party_member_index + 1):
                        self.game.party[j].x -= x
                        self.game.party[j].y -= y

                if args[2] != 0xFFFF:
                    self.game.update(False)
                self.game.make_scene()
                self.game.update_screen()
                self.game.delay_until(ticks)
                ticks = pg.time.get_ticks() + FRAME_TIME
                i += 1
                if i >= short(args[2]):
                    break

    def switch_day_night(self, *args):
        self.game.night_palette = not self.game.night_palette
        self.game.palette_fade(
            not args[0],
            self.game.num_palette,
            self.game.night_palette,
        )

    def jump_if_not_facing(self, *args):
        if not(
            self.game.scenes[self.game.num_scene - 1].event_object_index <
            args[0] <= self.game.scenes[self.game.num_scene].event_object_index
        ):
            self.script_entry = args[2] - 1
            self.mark_failed_script()
            return
        x = self.current.x
        y = self.current.y
        x += 16 if self.game.party_direction in {Direction.West, Direction.South} else -16
        y += 8 if self.game.party_direction in {Direction.West, Direction.North} else -8
        x -= pal_x(self.game.viewport) + pal_x(self.game.partyoffset)
        y -= pal_y(self.game.viewport) + pal_y(self.game.partyoffset)
        if abs(x) + abs(y * 2) < args[1] * 32 + 16:
            if args[1] > 0:
                self.current.trigger_mode = TriggerMode.TouchNormal + args[1]
        else:
            self.script_entry = args[2] - 1
            self.mark_failed_script()

    def npc_walk_highest(self, *args):
        if not self.game.npc_walk_to(
            self.event_object_id,
            args[0], args[1], args[2], 8
        ):
            self.script_entry -= 1

    def jump_by_npc_pos(self, *args):
        if not (
            self.game.scenes[self.game.num_scene - 1].event_object_index <
            args[0] <= self.game.scenes[self.game.num_scene].event_object_index
        ):
            self.script_entry = args[2] - 1
            self.mark_failed_script()
            return
        x = self.evt_obj.x - self.current.x
        y = self.evt_obj.y - self.current.y
        if abs(x) + abs(y * 2) >= args[1] * 32 + 16:
            self.script_entry = args[2] - 1
            self.mark_failed_script()

    def item_to_npc(self, *args):
        if not (
            self.game.scenes[self.game.num_scene - 1].event_object_index <
            args[0] <= self.game.scenes[self.game.num_scene].event_object_index
        ):
            self.script_entry = args[2] - 1
            self.mark_failed_script()
            return
        x = pal_x(self.game.viewport) + pal_x(self.game.partyoffset)
        y = pal_y(self.game.viewport) + pal_y(self.game.partyoffset)
        x += -16 if self.game.party_direction in {Direction.West, Direction.South} else 16
        y += -8 if self.game.party_direction in {Direction.West, Direction.North} else 8
        if self.game.check_obstacle((x, y), False, 0):
            self.script_entry = args[2] - 1
            self.mark_failed_script()
        else:
            self.current.x = x
            self.current.y = y
            self.current.state = short(args[1])

    def delay_a_period(self, *args):
        self.game.delay(args[0] * 80)

    def jump_by_not_equipped(self, *args):
        y = False
        i = 0
        while i <= self.game.max_party_member_index + 1:
            w = self.game.party[i].player_role
            for x in range(MAX_PLAYER_EQUIPMENTS):
                if self.game.player_roles.equipment[x][w] == args[0]:
                    y = True
                    i = 999
                    break
            i += 1
        if not y:
            self.script_entry = args[2] - 1

    def npc_walk_one_step(self, *args):
        self.game.npc_walk_one_step(self.cur_event_object_id, 0)

    def magic_damage_by_money(self, *args):
        i = min(self.game.cash, 5000)
        self.game.cash -= i
        j = self.game.objects[args[0]].magic.magic_number
        self.game.magics[j].base_damage = i * 2 // 5

    def set_battle_result(self, *args):
        self.game.battle.battle_result = args[0]

    def enable_auto_battle(self, *args):
        self.game.auto_battle = True

    def set_palette(self, *args):
        self.game.num_palette = args[0]
        if not self.game.need_fadein:
            self.game.set_palette(self.game.num_palette, False)

    def color_fade(self, *args):
        self.game.color_fade(args[1], byte(args[0]), args[2])
        self.game.need_fadein = False

    def inc_player_level(self, *args):
        self.game.player_level_up(self.event_object_id, args[0])

    def halve_cash(self, *args):
        self.game.cash //= 2

    def set_object_script(self, *args):
        self.game.objects[args[0]].data[2 + args[2]] = args[1]

    def jump_by_enemy_count(self, *args):
        if self.game.in_battle:
            for i in range(self.game.battle.max_enemy_index + 1):
                if (
                    i != self.event_object_id and
                    self.game.battle.enemies[i].object_id ==
                    self.game.battle.enemies[self.event_object_id].object_id
                ):
                    self.script_entry = args[0] - 1
                    break

    def show_magic_anim(self, *args):
        if self.game.in_battle:
            if args[0] != 0:
                self.game.battle_show_player_pre_magic_anim(args[0] - 1, False)
                self.game.battle.players[args[0] - 1].current_frame = 6
            for i in range(5):
                for j in range(self.game.max_party_member_index + 1):
                    self.game.battle.players[j].color_shift = i * 2
                self.game.battle_delay(1, 0, True)
            self.game.screen_bak.blit(self.game.battle.scene_buf, (0, 0))
            self.game.battle_update_fighters()
            self.game.battle_make_scene()
            self.game.battle_fade_scene()

    def screen_fade_update_scene(self, *args):
        self.game.scene_fade(
            short(args[0]), self.game.num_palette, self.game.night_palette
        )
        self.game.need_fadein = short(args[0]) < 0

    def jump_by_event(self, *args):
        if self.current.state == short(args[1]):
            self.script_entry = args[2] - 1

    def jump_by_scene(self, *args):
        if self.game.num_scene == args[0]:
            self.script_entry = args[1] - 1

    def ending_anim(self, *args):
        if not is_win95:
            self.game.ending_animation()

    def ride_event_object_high(self, *args):
        self.game.party_ride_event_object(
            self.event_object_id,
            args[0], args[1], args[2], 8
        )

    def set_party_follower(self, *args):
        if args[0] > 0:
            self.game.follower_num = 1
            self.game.party[self.game.max_party_member_index + 1].player_role = args[0]
            self.game.load_flags |= LoadResFlag.PlayerSprite
            self.game.load_resources()
            self.game.party[self.game.max_party_member_index + 1].x = self.game.trail[3].x - pal_x(self.game.viewport)
            self.game.party[self.game.max_party_member_index + 1].y = self.game.trail[3].y - pal_y(self.game.viewport)
            self.game.party[self.game.max_party_member_index + 1].frame = self.game.trail[3].direction * 3
        else:
            self.game.follower_num = 0

    def change_map(self, *args):
        if args[0] == 0xFFFF:
            self.game.scenes[self.game.num_scene - 1].map_num = args[1]
            self.game.load_flags |= LoadResFlag.Scene
            self.game.load_resources()
        else:
            self.game.scenes[args[0] - 1].map_num = args[1]

    def set_multi_npc_state(self, *args):
        for i in range(args[0], args[1] + 1):
            self.game.event_objects[i - 1].state = args[2]

    def fade_to_cur_scene(self, *args):
        self.backup_screen()
        self.game.make_scene()
        self.game.fade_screen(2)

    def divide_enemy(self, *args):
        w = 0
        for i in range(self.game.battle.max_enemy_index + 1):
            if self.game.battle.enemies[i].object_id != 0:
                w += 1
        if w != 1 or self.game.battle.enemies[self.cur_event_object_id].e.health <= 1:
            if args[1] != 0:
                self.script_entry = args[1] - 1
                return
        w = args[0] or 1
        for i in range(MAX_ENEMIES_IN_TEAM):
            if w > 0 and self.game.battle.enemies[i].object_id == 0:
                w -= 1
                enemy = BattleEnemy()
                enemy.object_id = self.game.battle.enemies[self.event_object_id].object_id
                enemy.e = self.game.battle.enemies[self.event_object_id].e.copy()
                enemy.e.health = (self.game.battle.enemies[self.event_object_id].e.health + w) // (w + 1)
                enemy.script_on_turn_start = self.game.battle.enemies[self.event_object_id].script_on_turn_start
                enemy.script_on_battle_end = self.game.battle.enemies[self.event_object_id].script_on_battle_end
                enemy.script_on_ready = self.game.battle.enemies[self.event_object_id].script_on_ready
                enemy.state = FighterState.Wait
                enemy.color_shift = 0
                self.game.battle.enemies[i] = enemy
        self.game.battle.enemies[self.event_object_id].e.health = (self.game.battle.enemies[self.event_object_id].e.health + w) // (w + 1)
        self.game.load_battle_sprites()
        for i in range(self.game.battle.max_enemy_index + 1):
            if self.game.battle.enemies[i].object_id == 0:
                continue
            self.game.battle.enemies[i].pos = self.game.battle.enemies[self.event_object_id].pos
        for i in range(10):
            for j in range(self.game.battle.max_enemy_index + 1):
                x = (
                    pal_x(self.game.battle.enemies[j].pos) +
                    pal_x(self.game.battle.enemies[j].pos_original)
                ) // 2
                y = (
                    pal_y(self.game.battle.enemies[j].pos) +
                    pal_y(self.game.battle.enemies[j].pos_original)
                ) // 2
                self.game.battle.enemies[j].pos = x, y
            self.game.battle_delay(1, 0, True)
        self.game.battle_update_fighters()
        self.game.battle_delay(1, 0, True)

    def enemy_summon_monster(self, *args):
        x = 0
        w = args[0]
        y = 1 if short(args[1]) <= 0 else short(args[1])
        enemy = self.game.battle.enemies[self.event_object_id]
        if w in {0, 0xFFFF}:
            w = enemy.object_id
        for i in range(self.game.battle.max_enemy_index + 1):
            if self.game.battle.enemies[i].object_id == 0:
                x += 1
        if (
            x < y or self.game.battle.hiding_time > 0 or
            enemy.status[Status.Sleep] != 0 or
            enemy.status[Status.Paralyzed] != 0 or
            enemy.status[Status.Confused] != 0
        ):
            if args[2] != 0:
                self.script_entry = args[2] - 1
        else:
            for i in range(self.game.battle.max_enemy_index + 1):
                if self.game.battle.enemies[i].object_id == 0:
                    enemy = BattleEnemy()
                    enemy.object_id = w
                    enemy.e = self.game.enemies[self.game.objects[w].enemy.enemy_id].copy()
                    enemy.state = FighterState.Wait
                    enemy.script_on_turn_start = self.game.objects[w].enemy.script_on_turn_start
                    enemy.script_on_battle_end = self.game.objects[w].enemy.script_on_battle_end
                    enemy.script_on_ready = self.game.objects[w].enemy.script_on_ready
                    enemy.color_shift = 8
                    self.game.battle.enemies[i] = enemy
                    y -= 1
                    if y == 0:
                        break
            self.game.battle_delay(2, 0, True)
            self.game.screen_bak.blit(self.game.battle.scene_buf, (0, 0))
            self.game.load_battle_sprites()
            self.game.battle_make_scene()
            self.game.play_sound(212)
            self.game.battle_fade_scene()
            for i in range(self.game.battle.max_enemy_index + 1):
                self.game.battle.enemies[i].color_shift = 0
            self.game.screen_bak.blit(self.game.battle.scene_buf, (0, 0))
            self.game.battle_make_scene()
            self.game.battle_fade_scene()

    def trans_enemy(self, *args):
        enemy = self.game.battle.enemies[self.event_object_id]
        if (
            self.game.battle.hiding_time <= 0 and
            enemy.status[Status.Sleep] == 0 and
            enemy.status[Status.Paralyzed] == 0 and
            enemy.status[Status.Confused] == 0
        ):
            w = enemy.e.health
            enemy.object_id = args[0]
            enemy.e = self.game.enemies[self.game.objects[args[0]].enemy.enemy_id].copy()
            enemy.e.health = w
            enemy.current_frame = 0
            for i in range(6):
                enemy.color_shift = i
                self.game.battle_delay(1, 0, False)
            enemy.color_shift = 0
            self.game.play_sound(47)
            self.game.screen_bak.blit(self.game.battle.scene_buf, (0, 0))
            self.game.load_battle_sprites()
            self.game.battle_make_scene()
            self.game.battle_fade_scene()

    def ending_credit_screen(self, *args):
        if is_win95:
            self.game.ending_screen()
        # self.game.additional_credits()
        self.game.shutdown(0)

    def join_group_pos(self, *args):
        for i in range(MAX_PLAYABLE_PLAYER_ROLES):
            self.game.trail[i].direction = self.game.party_direction
            self.game.trail[i].x = self.game.party[0].x + pal_x(self.game.viewport)
            self.game.trail[i].y = self.game.party[0].y + pal_y(self.game.viewport)
        for i in range(self.game.max_party_member_index + 1):
            self.game.party[i + 1].x = self.game.party[0].x
            self.game.party[i + 1].y = self.game.party[0].y - 1
        self.game.update_party_gestures(True)

    def random_command(self, *args):
        self.script_entry += random.randint(0, args[0] - 1)

    def play_cd_music(self, *args):
        if not self.game.play_cd_track(args[0]):
            self.game.play_music(args[1], True)

    def scroll_fbp(self, *args):
        if not is_win95:
            if args[0] == 68:
                self.game.show_fbp(69, 0)
            self.game.scroll_fbp(args[0], args[2], True)

    def show_fbp_sprite(self, *args):
        if not is_win95:
            if args[1] != 0xFFFF:
                self.game.cur_effect_sprite = args[1]
            self.game.show_fbp(args[0], args[2])

    def backup_screen(self, *args):
        self.game.screen_bak.blit(self.game.screen, (0, 0))

    commands = {
        0x0b: set_south_dir,
        0x0c: set_west_dir,
        0x0d: set_north_dir,
        0x0e: set_east_dir,
        0x0f: set_npc_dir,
        0x10: npc_walk,
        0x11: npc_walk_slow,
        0x12: set_npc_rel_pos,
        0x13: set_npc_pos,
        0x14: set_npc_frame,
        0x15: set_role_dir_frame,
        0x16: set_npc_dir_frame,
        0x17: set_extra_attr,
        0x18: equip_item,
        0x19: adjust_player_attr,
        0x1a: set_player_stat,
        0x1b: adjust_hp,
        0x1c: adjust_mp,
        0x1d: adjust_hp_mp,
        0x1e: set_money,
        0x1f: add_inventory,
        0x20: remove_inventory,
        0x21: inflict_damage,
        0x22: revive_player,
        0x23: remove_equip,
        0x24: set_npc_auto_script,
        0x25: set_npc_trigger_script,
        0x26: menu_buy,
        0x27: menu_sell,
        0x28: poison_enemy,
        0x29: poison_player,
        0x2a: cure_enemy,
        0x2b: cure_by_kind,
        0x2c: cure_by_level,
        0x2d: set_player_status,
        0x2e: set_enemy_status,
        0x2f: remove_player_status,
        0x30: inc_stat_temp,
        0x31: change_sprite_temp,
        0x33: collect_enemy_items,
        0x34: trans_enemy_items,
        0x35: shake_screen,
        0x36: set_rng,
        0x37: play_rng,
        0x38: teleport_party,
        0x39: drain_hp,
        0x3a: flee_from_battle,
        0x3f: ride_event_object_slow,
        0x40: set_trigger_mode,
        0x41: mark_failed_script,
        0x42: simulate_magic,
        0x43: play_music,
        0x44: ride_event_object_norm,
        0x45: set_battle_music,
        0x46: set_party_pos,
        0x47: play_sound,
        0x49: set_npc_state,
        0x4a: set_battle_field,
        0x4b: nullify_npc_a_while,
        0x4c: monster_chase_player,
        0x4d: wait_for_key,
        0x4e: load_last_save,
        0x4f: fade_to_red,
        0x50: fade_out,
        0x51: fade_in,
        0x52: hide_npc_a_while,
        0x53: set_day_palette,
        0x54: set_night_palette,
        0x55: add_player_magic,
        0x56: remove_player_magic,
        0x57: magic_damage_by_mp,
        0x58: jump_by_item_count,
        0x59: goto_scene,
        0x5a: halve_player_hp,
        0x5b: halve_enemy_hp,
        0x5c: hide_a_while,
        0x5d: jump_if_no_poison_kind,
        0x5e: jump_if_no_enemy_poison,
        0x5f: seckill_player,
        0x60: seckill_enemy,
        0x61: jump_if_no_poison_level,
        0x62: pause_chasing,
        0x63: speedup_chasing,
        0x64: jump_by_enemy_hp,
        0x65: set_player_sprite,
        0x66: throw_weapon,
        0x67: enemy_use_magic,
        0x68: jump_if_enemy_act,
        0x69: enemy_escape,
        0x6a: steal_from_enemy,
        0x6b: blow_away_enemies,
        0x6c: npc_walk_step,
        0x6d: set_scene_script,
        0x6e: move_player_one_step,
        0x6f: sync_npc_state,
        0x70: group_walk,
        0x71: wave_screen,
        0x73: fade_to_scene,
        0x74: if_lack_hp,
        0x75: set_role_group,
        0x76: show_fbp,
        0x77: stop_music,
        0x78: unknown,
        0x79: jump_by_specific_player,
        0x7a: group_walk_high,
        0x7b: group_walk_highest,
        0x7c: npc_walk_high,
        0x7d: npc_move,
        0x7e: set_npc_layer,
        0x7f: move_viewport,
        0x80: switch_day_night,
        0x81: jump_if_not_facing,
        0x82: npc_walk_highest,
        0x83: jump_by_npc_pos,
        0x84: item_to_npc,
        0x85: delay_a_period,
        0x86: jump_by_not_equipped,
        0x87: npc_walk_one_step,
        0x88: magic_damage_by_money,
        0x89: set_battle_result,
        0x8a: enable_auto_battle,
        0x8b: set_palette,
        0x8c: color_fade,
        0x8d: inc_player_level,
        0x8f: halve_cash,
        0x90: set_object_script,
        0x91: jump_by_enemy_count,
        0x92: show_magic_anim,
        0x93: screen_fade_update_scene,
        0x94: jump_by_event,
        0x95: jump_by_scene,
        0x96: ending_anim,
        0x97: ride_event_object_high,
        0x98: set_party_follower,
        0x99: change_map,
        0x9a: set_multi_npc_state,
        0x9b: fade_to_cur_scene,
        0x9c: divide_enemy,
        0x9e: enemy_summon_monster,
        0x9f: trans_enemy,
        0xa0: ending_credit_screen,
        0xa1: join_group_pos,
        0xa2: random_command,
        0xa3: play_cd_music,
        0xa4: scroll_fbp,
        0xa5: show_fbp_sprite,
        0xa6: backup_screen,
    }


class AutoScriptContext(object):
    commands = {}

    def __init__(self, game, script_entry, event_object_id):
        self.script_entry = script_entry
        self.event_object_id = event_object_id
        self.game = game

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        del self.game

    @property
    def evt_obj(self):
        return self.game.event_objects[self.event_object_id - 1]

    def begin(self):
        script = self.game.scripts[self.script_entry]
        if script.op in self.commands:
            self.commands[script.op](
                self, *script.params
            )
        else:
            self.script_entry = self.game.interprete(
                self.script_entry,
                self.event_object_id
            )

    def finish_code(self, *args):
        pass
    commands[0x00] = finish_code

    def stop_code(self, *args):
        self.script_entry += 1
    commands[0x01] = stop_code

    def change_script(self, *args):
        if args[1] == 0:
            self.script_entry = args[0]
        else:
            self.evt_obj.script_idle_frame_count_auto += 1
            if self.evt_obj.script_idle_frame_count_auto < args[1]:
                self.script_entry = args[0]
            else:
                self.evt_obj.script_idle_frame_count_auto = 0
                self.script_entry += 1
    commands[0x02] = change_script

    def goto_script(self, *args):
        if args[1] == 0:
            self.script_entry = args[0]
            self.begin()
        else:
            self.evt_obj.script_idle_frame_count_auto += 1
            if self.evt_obj.script_idle_frame_count_auto < args[1]:
                self.script_entry = args[0]
                self.begin()
            else:
                self.evt_obj.script_idle_frame_count_auto = 0
                self.script_entry += 1
    commands[0x03] = goto_script

    def sub_script(self, *args):
        self.game.run_trigger_script(
            args[0],
            args[1] if args[1] else self.event_object_id
        )
        self.script_entry += 1
    commands[0x04] = sub_script

    def random_script(self, *args):
        if random.randint(1, 100) >= args[0]:
            if args[1] != 0:
                self.script_entry = args[1]
                self.begin()
        else:
            self.script_entry += 1
    commands[0x06] = random_script

    def update_screen_and_wait(self, *args):
        self.evt_obj.script_idle_frame_count_auto += 1
        if self.evt_obj.script_idle_frame_count_auto >= args[0]:
            self.evt_obj.script_idle_frame_count_auto = 0
            self.script_entry += 1
    commands[0x09] = update_screen_and_wait

    def next_script(self, *args):
        self.script_entry += 1
    commands[0xa7] = next_script

    def show_desc(self, *args):
        if is_win95:
            x_base = 71 if self.event_object_id & PAL_ITEM_DESC_BOTTOM else 102
            y_base = (
                151 - pal_x(self.game.screen_layout.extra_item_desc_lines) * 16 if
                self.event_object_id & PAL_ITEM_DESC_BOTTOM else 3
            )
            desc_line = self.event_object_id & ~PAL_ITEM_DESC_BOTTOM
            if config['msg_file']:
                group = self.game.msg_index[args[0]]
                for msg in group:
                    if msg > 0:
                        self.game.draw_text(
                            self.game.msgs[msg], (x_base, desc_line * 16 + y_base),
                            DESCTEXT_COLOR, True, False
                        )
                        desc_line += 1
                while self.game.scripts[self.script_entry].op == 0xFFFF:
                    self.script_entry += 1
            else:
                self.game.draw_text(
                    self.game.msgs[args[0]], (x_base, desc_line * 16 + y_base),
                    DESCTEXT_COLOR, True, False
                )
                self.script_entry += 1
        else:
            self.script_entry += 1
    commands[0xffff] = show_desc


class TriggerScriptContext(object):
    last_event_object = 0
    commands = {}

    def __init__(self, game, script_entry, event_object_id):
        self.game = game
        self.game.updated_in_battle = False
        self.ended = False
        self.script_entry = script_entry
        self.next_script_entry = script_entry
        if event_object_id == 0xffff:
            event_object_id = self.last_event_object
        self.event_object_id = event_object_id
        type(self).last_event_object = event_object_id
        self.game.delay_time = 3
        RunResult.success = True
        while self.script_entry != 0 and not self.ended:
            script = self.game.scripts[self.script_entry]
            if script.op in self.commands:
                self.commands[script.op](
                    self, *script.params
                )
            else:
                self.game.clear_dialog(True)
                self.script_entry = self.game.interprete(
                    self.script_entry,
                    self.event_object_id
                )
        self.game.end_dialog()
        self.game.cur_equip_part = -1

    @property
    def evt_obj(self):
        return self.game.event_objects[self.event_object_id - 1]

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        del self.game

    def finish_code(self, *args):
        self.ended = True
    commands[0x00] = finish_code

    def stop_code(self, *args):
        self.ended = True
        self.next_script_entry = self.script_entry + 1
    commands[0x01] = stop_code

    def change_script(self, *args):
        if args[1] == 0:
            self.ended = True
            self.next_script_entry = args[0]
        else:
            self.evt_obj.script_idle_frame += 1
            if self.evt_obj.script_idle_frame < args[1]:
                self.ended = True
                self.next_script_entry = args[0]
            else:
                self.evt_obj.script_idle_frame = 0
                self.script_entry += 1
    commands[0x02] = change_script

    def goto_script(self, *args):
        if args[1] == 0:
            self.script_entry = args[0]
        else:
            self.evt_obj.script_idle_frame += 1
            if self.evt_obj.script_idle_frame < args[1]:
                self.script_entry = args[0]
            else:
                self.evt_obj.script_idle_frame = 0
                self.script_entry += 1
    commands[0x03] = goto_script

    def sub_script(self, *args):
        self.game.run_trigger_script(
            args[0],
            args[1] if args[1] else self.event_object_id
        )
        self.script_entry += 1
    commands[0x04] = sub_script

    def redraw_screen(self, *args):
        self.game.clear_dialog(True)
        if self.game.playing_rng:
            self.game.blit(self.game.screen_bak, (0, 0))
        elif self.game.in_battle:
            self.game.battle_make_scene()
            self.game.blit(self.game.battle.scene_buf, (0, 0))
            self.game.update_screen()
        else:
            if args[2]:
                self.game.update_party_gestures(False)
            self.game.make_scene()
            self.game.update_screen()
            self.game.delay(max(args[1], 1) * 60)
        self.script_entry += 1
    commands[0x05] = redraw_screen

    def random_script(self, *args):
        if random.randint(1, 100) >= args[0]:
            self.script_entry = args[1]
        else:
            self.script_entry += 1
    commands[0x06] = random_script

    def start_battle(self, *args):
        i = self.game.start_battle(args[0], not args[2])
        if i == BattleResult.Lost and args[1] != 0:
            self.script_entry = args[1]
        elif i == BattleResult.Fleed and args[2] != 0:
            self.script_entry = args[2]
        else:
            self.script_entry += 1
        self.game.auto_battle = False
    commands[0x07] = start_battle

    def change_entry(self, *args):
        self.script_entry += 1
        self.next_script_entry = self.script_entry
    commands[0x08] = change_entry

    def update_screen_and_wait(self, *args):
        self.game.clear_dialog(True)
        t = pg.time.get_ticks() + FRAME_TIME
        for _ in range(max(args[0], 1)):
            self.game.delay_until(t)
            t = pg.time.get_ticks() + FRAME_TIME
            if args[2]:
                self.game.update_party_gestures(False)
            self.game.update(bool(args[1]))
            self.game.make_scene()
            self.game.update_screen()
        self.script_entry += 1
    commands[0x09] = update_screen_and_wait

    def goto_address(self, *args):
        self.game.clear_dialog(False)
        if not self.game.confirm_menu():
            self.script_entry = args[0]
        else:
            self.script_entry += 1
    commands[0x0a] = goto_address

    def middle_dlg(self, *args):
        self.game.clear_dialog(True)
        self.game.start_dialog(
            DialogPos.Center, byte(args[0]),
            0, bool(args[2])
        )
        self.script_entry += 1
    commands[0x3b] = middle_dlg

    def upper_dlg(self, *args):
        self.game.clear_dialog(True)
        self.game.start_dialog(
            DialogPos.Upper, byte(args[1]),
            args[0], bool(args[2])
        )
        self.script_entry += 1
    commands[0x3c] = upper_dlg

    def lower_dlg(self, *args):
        self.game.clear_dialog(True)
        self.game.start_dialog(
            DialogPos.Lower, byte(args[1]),
            args[0], bool(args[2])
        )
        self.script_entry += 1
    commands[0x3d] = lower_dlg

    def center_window_dlg(self, *args):
        self.game.clear_dialog(True)
        self.game.start_dialog(
            DialogPos.CenterWindow, byte(args[0]),
            0, False
        )
        self.script_entry += 1
    commands[0x3e] = center_window_dlg

    def restore_screen(self, *args):
        self.game.clear_dialog(True)
        self.game.blit(self.game.screen_bak, (0, 0))
        self.game.update_screen()
        self.script_entry += 1
    commands[0x8e] = restore_screen

    def dlg_text(self, *args):
        if config['msg_file']:
            group = self.game.msg_index[args[0]]
            for msg in group:
                if msg == 0:
                    self.restore_screen()
                    self.script_entry -= 1
                else:
                    self.game.show_dialog_text(self.game.msgs[msg])
            if self.game.scripts[self.script_entry + 1].op == 0xFFFF and self.game.scripts[self.script_entry + 1].p1 != args[0] + 1:
                self.script_entry += 1
            else:
               while self.game.scripts[self.script_entry].op in {0xFFFF, 0x008E}:
                   self.script_entry += 1
        else:
            self.game.show_dialog_text(self.game.msgs[args[0]])
            self.script_entry += 1
    commands[0xffff] = dlg_text


class ScriptRunnerMixin(object):
    def run_trigger_script(self, script_entry, event_object_id):
        with TriggerScriptContext(self, script_entry, event_object_id) as ctx:
            return ctx.next_script_entry

    def interprete(self, script_entry, event_object_id):
        with InterpreterContext(self, script_entry, event_object_id) as ctx:
            return ctx.script_entry + 1

    def run_auto_script(self, script_entry, event_object_id):
        with AutoScriptContext(self, script_entry, event_object_id) as ctx:
            ctx.begin()
            return ctx.script_entry

    def npc_walk_to(self, event_object_id, x, y, h, speed):
        evt_obj = self.event_objects[event_object_id - 1]
        x_offset = (x * 32 + h * 16) - evt_obj.x
        y_offset = (y * 16 + h * 8) - evt_obj.y
        if y_offset < 0:
            evt_obj.direction = Direction.West if x_offset < 0 else Direction.North
        else:
            evt_obj.direction = Direction.South if x_offset < 0 else Direction.East
        if abs(x_offset) < speed * 2 or abs(y_offset) < speed * 2:
            evt_obj.x = x * 32 + h * 16
            evt_obj.y = y * 16 + h * 8
        else:
            self.npc_walk_one_step(event_object_id, speed)
        if (
            evt_obj.x == x * 32 + h * 16 and
            evt_obj.y == y * 16 + h * 8
        ):
            evt_obj.current_frame_num = 0
            return True
        return False

    def party_walk_to(self, x, y, h, speed):
        x_offset = x * 32 + h * 16 - pal_x(self.viewport) - pal_x(self.partyoffset)
        y_offset = y * 16 + h * 8 - pal_y(self.viewport) - pal_y(self.partyoffset)
        t = 0
        while not x_offset == y_offset == 0:
            self.delay_until(t)
            t = pg.time.get_ticks() + FRAME_TIME
            for i in range(4, 0, -1):
                self.trail[i] = self.trail[i - 1]
            self.trail[0].direction = self.party_direction
            self.trail[0].x = pal_x(self.viewport) + pal_x(self.partyoffset)
            self.trail[0].y = pal_y(self.viewport) + pal_y(self.partyoffset)
            if y_offset < 0:
                self.party_direction = Direction.West if x_offset < 0 else Direction.North
            else:
                self.party_direction = Direction.South if x_offset < 0 else Direction.East
            dx, dy = self.viewport
            if abs(x_offset) <= speed * 2:
                dx += x_offset
            else:
                dx += speed * (-2 if x_offset < 0 else 2)
            if abs(y_offset) <= speed:
                dy += y_offset
            else:
                dy += speed * (-1 if y_offset < 0 else 1)
            self.viewport = dx, dy
            self.update_party_gestures(True)
            self.update(False)
            self.make_scene()
            self.update_screen()
            x_offset = x * 32 + h * 16 - pal_x(self.viewport) - pal_x(self.partyoffset)
            y_offset = y * 16 + h * 8 - pal_y(self.viewport) - pal_y(self.partyoffset)
        self.update_party_gestures(False)

    def party_ride_event_object(self, event_object_id, x, y, h, speed):
        p = self.event_objects[event_object_id - 1]
        x_offset = x * 32 + h * 16 - pal_x(self.viewport) - pal_x(self.partyoffset)
        y_offset = y * 16 + h * 8 - pal_y(self.viewport) - pal_y(self.partyoffset)
        t = 0
        while not x_offset == y_offset == 0:
            self.delay_until(t)
            t = pg.time.get_ticks() + FRAME_TIME
            if y_offset < 0:
                self.party_direction = Direction.West if x_offset < 0 else Direction.North
            else:
                self.party_direction = Direction.South if x_offset < 0 else Direction.East
            if abs(x_offset) > speed * 2:
                dx = speed * (-2 if x_offset < 0 else 2)
            else:
                dx = x_offset
            if abs(y_offset) > speed:
                dy = speed * (-1 if y_offset < 0 else 1)
            else:
                dy = y_offset
            for i in range(4, 0, -1):
                self.trail[i] = self.trail[i - 1]
            self.trail[0].direction = self.party_direction
            self.trail[0].x = pal_x(self.viewport) + dx + pal_x(self.partyoffset)
            self.trail[0].y = pal_y(self.viewport) + dy + pal_y(self.partyoffset)
            self.viewport = (pal_x(self.viewport) + dx, pal_y(self.viewport) + dy)
            p.x += dx
            p.y += dy
            self.update(False)
            self.make_scene()
            self.update_screen()
            x_offset = x * 32 + h * 16 - pal_x(self.viewport) - pal_x(self.partyoffset)
            y_offset = y * 16 + h * 8 - pal_y(self.viewport) - pal_y(self.partyoffset)

    def monster_chase_player(self, event_object_id, speed, chase_range, floating):
        evt_obj = self.event_objects[event_object_id - 1]
        monster_speed = 0
        if self.chase_range != 0:
            x = pal_x(self.viewport) + pal_x(self.partyoffset) - evt_obj.x
            y = pal_y(self.viewport) + pal_y(self.partyoffset) - evt_obj.y
            if x == 0:
                x = -1 if random.randint(0, 1) else 1
            if y == 0:
                y = -1 if random.randint(0, 1) else 1
            prev_x = evt_obj.x
            prev_y = evt_obj.y
            i = prev_x % 32
            j = prev_y % 16
            prev_x //= 32
            prev_y //= 16
            l = 0
            if i + j * 2 >= 16:
                if i + j * 2 >= 48:
                    prev_x += 1
                    prev_y += 1
                elif 32 - i + j * 2 < 16:
                    prev_x += 1
                elif 32 - i + j * 2 < 48:
                    l = 1
                else:
                    prev_y += 1
            prev_x = prev_x * 32 + l * 16
            prev_y = prev_y * 16 + l * 8
            if abs(x) + abs(y) * 2 < chase_range * 32 * self.chase_range:
                if x < 0:
                    if y < 0:
                        evt_obj.direction = Direction.West
                    else:
                        evt_obj.direction = Direction.South
                else:
                    if y < 0:
                        evt_obj.direction = Direction.North
                    else:
                        evt_obj.direction = Direction.East
                if x != 0:
                    x = evt_obj.x + x // abs(x) * 16
                else:
                    x = evt_obj.x
                if y != 0:
                    y = evt_obj.y + y // abs(y) * 8
                else:
                    y = evt_obj.y
                if floating:
                    monster_speed = speed
                else:
                    if not self.check_obstacle((x, y), True, event_object_id):
                        monster_speed = speed
                    else:
                        evt_obj.x = prev_x
                        evt_obj.y = prev_y
                    for l in range(4):
                        if l == 0:
                            evt_obj.x -= 4
                            evt_obj.y += 2
                        elif l == 1:
                            evt_obj.x -= 4
                            evt_obj.y -= 2
                        elif l == 2:
                            evt_obj.x += 4
                            evt_obj.y -= 2
                        elif l == 3:
                            evt_obj.x += 4
                            evt_obj.y += 2
                        if self.check_obstacle((evt_obj.x, evt_obj.y), False, 0):
                            evt_obj.x = prev_x
                            evt_obj.y = prev_y
        self.npc_walk_one_step(event_object_id, monster_speed)

