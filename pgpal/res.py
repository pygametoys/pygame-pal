# -*- coding: utf8 -*-
from pgpal.mkfext import SSS, Data, GOPS
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.text import Msg
from pgpal.utils import Structure, WORD, SHORT, read_by_struct


class Event(Structure):
    _fields_ = [  
        ('h',          'vanish_time'),
        ('H',          'x'),
        ('H',          'y'),
        ('h',          'layer'),
        ('H',          'trigger_script'),
        ('H',          'auto_script'),
        ('h',          'state'),
        ('H',          'trigger_mode'),
        ('H',          'sprite_num'),
        ('H',          'sprite_frames_num'),
        ('H',          'direction'),
        ('H',          'current_frame_num'),
        ('H',          'script_idle_frame'),
        ('H',          'sprite_offset'),
        ('H',          'sprite_frames_auto'),
        ('H',          'script_idle_frame_count_auto'),
    ]

    @property
    def current_frame(self):
        return self.sprite_frames_num * self.direction + self.current_frame_num

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos):
        self.x, self.y = pos


class ScriptEntry(Structure):
    _fields_ = [
        ('H', 'op'),
        ('H', 'p1'),
        ('H', 'p2'),
        ('H', 'p3'),
    ]

    @property
    def params(self):
        return self.p1, self.p2, self.p3


class Item(Structure):
    _fields_ = [
        ('H', 'bitmap'),
        ('H', 'price'),
        ('H', 'script_on_use'),
        ('H', 'script_on_equip'),
        ('H', 'script_on_throw'),
        ('H', 'flags'),
    ]
    if is_win95:
        _fields_.insert(-1, ('H', 'script_desc'))


Store = WORD * MAX_STORE_ITEM


class Enemy(Structure):
    _fields_ = [
        ('H', 'idle_frames'),
        ('H', 'magic_frames'),
        ('H', 'attack_frames'),
        ('H', 'idle_anim_speed'),
        ('H', 'act_wait_frames'),
        ('H', 'y_pos_offset'),
        ('h', 'attack_sound'),
        ('h', 'action_sound'),
        ('h', 'magic_sound'),
        ('h', 'death_sound'),
        ('h', 'call_sound'),
        ('h', 'health'),
        ('H', 'exp'),
        ('H', 'cash'),
        ('H', 'level'),
        ('H', 'magic'),
        ('H', 'magic_rate'),
        ('H', 'attack_equiv_item'),
        ('H', 'attack_equiv_item_rate'),
        ('H', 'steal_item'),
        ('H', 'steal_item_num'),
        ('h', 'attack_strength'),
        ('h', 'magic_strength'),
        ('h', 'defense'),
        ('h', 'dexterity'),
        ('H', 'flee_rate'),
        ('H', 'poison_resistance'),
        (WORD * NUM_MAGIC_ELEMENTAL, 'elem_resistance'),
        ('H', 'physical_resistance'),
        ('H', 'dual_move'),
        ('H', 'collect_value'),
    ]


EnemyTeam = WORD * MAX_ENEMIES_IN_TEAM


class Magic(Structure):
    _fields_ = [
        ('H', 'effect'),
        ('H', 'type'),
        ('h', 'x_offset'),
        ('h', 'y_offset'),
        ('H', 'summon_effect'),
        ('h', 'speed'),
        ('H', 'keep_effect'),
        ('H', 'fire_delay'),
        ('h', 'effect_times'),
        ('H', 'shake'),
        ('H', 'wave'),
        ('H', 'unknown'),
        ('H', 'cost_mp'),
        ('h', 'base_damage'),
        ('H', 'elemental'),
        ('h', 'sound'),
    ]


class BattleField(Structure):
    _fields_ = [
        ('H', 'screen_wave'),
        (SHORT * NUM_MAGIC_ELEMENTAL, 'magic_effect')
    ]


class LevelUpMagic(Structure):
    _fields_ = [
        ('H', 'level'),
        ('H', 'magic'),
    ]


LevelUpMagic_All = LevelUpMagic * MAX_PLAYABLE_PLAYER_ROLES


class PalPos(Structure):
    _fields_ = [
        ('H', 'x'),
        ('H', 'y'),
    ]


class EnemyPos(Structure):
    _fields_ = [
        (PalPos * MAX_ENEMIES_IN_TEAM * MAX_ENEMIES_IN_TEAM, 'pos')
    ]


BattleEffectIndex = WORD * 2 * 10

LevelUpExp = WORD * (MAX_LEVELS + 1)


class ResourceManagerMixin(object):
    def __init__(self):
        self.load_flags = 0
        self.event_object_sprites = None
        self.event_object_num = 0
        self.player_sprites = [None] * (MAX_PLAYERS_IN_PARTY + 1)
        self.msgs = Msg()
        self.gops = GOPS()
        self.sss = SSS()
        self.data = Data()

    def load_resources(self):
        if self.load_flags == 0:
            return
        if self.load_flags & LoadResFlag.Scene:
            if self.entering_scene:
                self.screen_wave = 0
                self.wave_progression = 0
            self.event_object_sprites = None
            i = self.num_scene - 1
            self.maps.load(self.scenes[i].map_num, self.gops)
            index = self.scenes[i].event_object_index
            self.event_object_num = self.scenes[i + 1].event_object_index - index
            if self.event_object_num > 0:
                self.event_object_sprites = [None] * self.event_object_num
            for i in range(self.event_object_num):
                n = self.event_objects[index].sprite_num
                if n == 0:
                    index += 1
                    continue
                self.event_object_sprites[i] = self.mgo[n]
                if self.event_object_sprites[i] is not None:
                    self.event_objects[index].sprite_frames_auto = len(
                        self.event_object_sprites[i]
                    )
                index += 1
            self.partyoffset = 160, 112
        if self.load_flags & LoadResFlag.PlayerSprite:
            self.player_sprites = [None] * (MAX_PLAYERS_IN_PARTY + 1)
            for i in range(self.max_party_member_index + 1):
                player_id = self.party[i].player_role
                assert player_id < MAX_PLAYER_ROLES
                sprite_num = self.player_roles.sprite_num[player_id]
                self.player_sprites[i] = self.mgo[sprite_num]
            i = self.max_party_member_index + 1
            if self.follower_num > 0:
                sprite_num = self.party[i].player_role
                self.player_sprites[i] = self.mgo[sprite_num]
        self.load_flags = 0

    def init_global_game_data(self):

        self.scripts = read_by_struct(ScriptEntry, self.sss.read(4))

        self.store = read_by_struct(Store, self.data.read(0))

        self.enemies = read_by_struct(Enemy, self.data.read(1))

        self.enemy_team = read_by_struct(EnemyTeam, self.data.read(2))

        self.magics = read_by_struct(Magic, self.data.read(4, True))

        self.battle_fields = read_by_struct(BattleField, self.data.read(5))

        self.level_up_magics = read_by_struct(LevelUpMagic_All, self.data.read(6))

        self.battle_effect_index = read_by_struct(
            BattleEffectIndex, self.data.read(11)
        )[0]

        self.enemy_pos = read_by_struct(EnemyPos, self.data.read(13))[0]

        self.level_up_exp = read_by_struct(LevelUpExp, self.data.read(14))[0]

    def get_event_object_sprite(self, event_object_id):
        event_object_id -= self.scenes[self.num_scene - 1].event_object_index
        event_object_id -= 1
        if event_object_id >= self.event_object_num:
            return
        return self.event_object_sprites[event_object_id]
