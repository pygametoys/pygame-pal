# -*- coding: utf8 -*-
import os
from struct import unpack
from pgpal.player import *
from pgpal.res import Event
from pgpal.scene import Scene
from pgpal.utils import read_by_struct
from pgpal import config
from pgpal.compat import range, FileNotFoundError, open_ignore_case as open


class SetupStruct(Structure):
    _fields_ = [
        ('H', 'key_leftup'),
        ('H', 'key_rightup'),
        ('H', 'key_rightdown'),
        ('H', 'key_leftdown'),
        ('H', 'music'),
        ('H', 'sound'),
        ('H', 'irq'),
        ('H', 'io_port'),
        ('H', 'midi'),
        ('H', 'use_files_on_cd'),
    ]


PoisonStatusTable = PoisonStatus * MAX_PLAYABLE_PLAYER_ROLES * MAX_POISONS


class SavedGame(Structure):
    _fields_ = [
        ('H', 'saved_times'),
        ('H', 'x'),
        ('H', 'y'),
        ('H', 'party_member_num'),
        ('H', 'num_scene'),
        ('H', 'palette_offset'),
        ('H', 'party_direction'),
        ('H', 'num_music'),
        ('H', 'num_battle_music'),
        ('H', 'num_battle_field'),
        ('H', 'screen_wave'),
        ('H', 'battle_speed'),
        ('H', 'collect_value'),
        ('H', 'layer'),
        ('H', 'chase_range'),
        ('H', 'chasespeed_change_cycles'),
        ('H', 'follower_num'),
        ('3H', 'reserved2'),
        ('I', 'cash'),
        (Party * MAX_PLAYABLE_PLAYER_ROLES, 'party'),
        (Trail * MAX_PLAYABLE_PLAYER_ROLES, 'trail'),
        (AllExperience, 'exp'),
        (PlayerRoles, 'player_roles'),
        (PoisonStatusTable, 'poison_status'),
        (Inventory * MAX_INVENTORY, 'inventory'),
        (Scene * MAX_SCENES, 'scene'),
        (Obj * MAX_OBJECTS, 'object'),
        (Event * MAX_EVENT_OBJECTS, 'event_object')
    ]

    @property
    def viewport(self):
        return self.x, self.y

    @viewport.setter
    def viewport(self, pos):
        self.x, self.y = pos


class SaveLoadMixin(object):
    def __init__(self):
        self.cur_save_slot = 1

    def get_saved_times(self, index, path=None):
        if path is None:
            path = str(index) + '.rpg'
        try:
            with open(path, 'rb') as fin:
                head = fin.read(2)
                if len(head):
                    return unpack('H', head)[0]
                else:
                    return 0
        except FileNotFoundError:
            return 0

    def init_game_data(self, slot):
        self.init_global_game_data()
        self.cur_save_slot = slot
        self.load_game(slot)
        self.to_start = True
        self.need_fadein = False
        self.cur_inv_menu_item = 0
        self.in_battle = False
        self.player_status = PlayerStatus(None)
        self.update_equipments()

    def load_default_game(self):
        save = SavedGame(None)
        self.saved_times = 0
        self.event_objects = read_by_struct(
            Event,
            self.sss.read(0, True)
        )
        self.scenes = read_by_struct(
            Scene,
            self.sss.read(1, True).ljust(save.scene.struct_size, b'\x00')
        )
        self.objects = read_by_struct(
            Obj,
            self.sss.read(2, True).ljust(save.object.struct_size, b'\x00')
        )
        self.player_roles = PlayerRoles(
            self.data.read(3, True).ljust(PlayerRoles.struct_size, b'\x00')
        )
        self.battle_speed = 2
        self.cash = 0
        self.num_music = 0
        self.num_palette = 0
        self.num_scene = 1
        self.collect_value = 0
        self.night_palette = False
        self.max_party_member_index = 0
        self.viewport = 0, 0
        self.layer = 0
        self.chase_range = 1
        self.party_direction = save.party_direction
        self.inventory = save.inventory
        self.poison_status = save.poison_status
        self.party = save.party
        self.trail = save.trail
        self.exp = save.exp
        self.chasespeed_change_cycles = save.chasespeed_change_cycles
        self.follower_num = save.follower_num
        for i in range(MAX_PLAYER_ROLES):
            self.exp.primary_exp[i].level = self.player_roles.level[i]
            self.exp.health_exp[i].level = self.player_roles.level[i]
            self.exp.magic_exp[i].level = self.player_roles.level[i]
            self.exp.attack_exp[i].level = self.player_roles.level[i]
            self.exp.magic_power_exp[i].level = self.player_roles.level[i]
            self.exp.defense_exp[i].level = self.player_roles.level[i]
            self.exp.dexterity_exp[i].level = self.player_roles.level[i]
            self.exp.flee_exp[i].level = self.player_roles.level[i]
        self.entering_scene = True

    def load_game(self, index, path=None):
        if index == 0:
            self.load_default_game()
            return
        try:
            if path is None:
                path = '%d.rpg' % index
            with open(path, 'rb') as f:
                save = SavedGame.from_file(f)
                self.battle_speed = save.battle_speed
                self.cash = save.cash
                self.viewport = save.viewport
                self.max_party_member_index = save.party_member_num
                self.num_scene = save.num_scene
                self.night_palette = save.palette_offset != 0
                self.party_direction = save.party_direction
                self.num_music = save.num_music
                self.num_battle_music = save.num_battle_music
                self.num_battle_field = save.num_battle_field
                self.screen_wave = save.screen_wave
                self.wave_progression = 0
                self.collect_value = save.collect_value
                self.layer = save.layer
                self.chase_range = save.chase_range
                self.chasespeed_change_cycles = save.chasespeed_change_cycles
                self.follower_num = save.follower_num
                self.party = save.party
                self.trail = save.trail
                self.exp = save.exp
                self.player_roles = save.player_roles
                self.poison_status = PoisonStatusTable(None)
                self.inventory = save.inventory
                self.scenes = read_by_struct(Scene, save.scene._buffer)
                self.event_objects = read_by_struct(Event, save.event_object._buffer)
                self.objects = read_by_struct(Obj, save.object._buffer)
                self.entering_scene = False
                self.compress_inventory()
        except Exception:
            self.load_default_game()

    def save_game(self, index, saved_times, path=None):
        if path is None:
            path = '%d.rpg' % index
        save = SavedGame(None)
        save.saved_times = saved_times
        save.viewport = self.viewport
        save.party_member_num = self.max_party_member_index
        save.num_scene = self.num_scene
        save.palette_offset = 0x180 if self.night_palette else 0
        save.party_direction = self.party_direction
        save.num_music = self.num_music
        save.num_battle_music = self.num_battle_music
        save.num_battle_field = self.num_battle_field
        save.screen_wave = self.screen_wave
        save.collect_value = self.collect_value
        save.layer = self.layer
        save.chase_range = self.chase_range
        save.chasespeed_change_cycles = self.chasespeed_change_cycles
        save.follower_num = self.follower_num
        save.cash = self.cash
        save.battle_speed = 2
        save.party = self.party
        save.trail = self.trail
        save.exp = self.exp
        save.poison_status = self.poison_status
        save.inventory = self.inventory
        save.player_roles = self.player_roles
        for i, _ in enumerate(self.event_objects):
            save.event_object[i] = self.event_objects[i]
        for i, _ in enumerate(self.objects):
            save.object[i] = self.objects[i]
        for i, _ in enumerate(self.scenes):
            save.scene[i] = self.scenes[i]
        with open(path, 'wb') as f:
            f.write(save._buffer.tobytes()[
                :len(self.sss.read(0)) +
                save.struct_size -
                Event.struct_size * MAX_EVENT_OBJECTS
            ])
