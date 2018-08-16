# -*- coding: utf8 -*-
from random import randint
from struct import pack_into
from pgpal.compat import range, partialmethod
from pgpal.const import *
from pgpal.mkfbase import is_win95
from pgpal.res import Item
from pgpal.utils import Structure, WORD, short


class Sprite(pg.sprite.DirtySprite):
    def __init__(self, frame=0, pos=(0, 0), layer=0):
        pg.sprite.DirtySprite.__init__(self)
        self.frame = frame
        self.pos = pos
        self.layer = layer


class Party(Structure):
    _fields_ = [
        ('H',             'player_role'),
        ('h',             'x'),
        ('h',             'y'),
        ('H',             'frame'),
        ('H',             'image_offset')
    ]


class Trail(Structure):
    _fields_ = [
        ('H',             'x'),
        ('H',             'y'),
        ('H',             'direction')
    ]


class Experience(Structure):
    _fields_ = [
        ('H',             'exp'),
        ('H',             'reserved'),
        ('H',             'level'),
        ('H',             'count')
    ]


class AllExperience(Structure):
    _fields_ = [
        (Experience * MAX_PLAYER_ROLES, 'primary_exp'),
        (Experience * MAX_PLAYER_ROLES, 'health_exp'),
        (Experience * MAX_PLAYER_ROLES, 'magic_exp'),
        (Experience * MAX_PLAYER_ROLES, 'attack_exp'),
        (Experience * MAX_PLAYER_ROLES, 'magic_power_exp'),
        (Experience * MAX_PLAYER_ROLES, 'defense_exp'),
        (Experience * MAX_PLAYER_ROLES, 'dexterity_exp'),
        (Experience * MAX_PLAYER_ROLES, 'flee_exp'),
    ]


class Players(Structure):
    _fields_ = [
        ('h', i)
        for i in range(MAX_PLAYER_ROLES)
    ]


PlayerStatus = WORD * Status.All * MAX_PLAYER_ROLES


class PlayerRoles(Structure):
    _fields_ = [
        (Players, 'avatar'),
        (Players, 'sprite_num_in_battle'),
        (Players, 'sprite_num'),
        (Players, 'name'),
        (Players, 'attack_all'),
        (Players, 'unknown1'),
        (Players, 'level'),
        (Players, 'max_hp'),
        (Players, 'max_mp'),
        (Players, 'hp'),
        (Players, 'mp'),
        (Players * MAX_PLAYER_EQUIPMENTS, 'equipment'),
        (Players, 'attack_strength'),
        (Players, 'magic_strength'),
        (Players, 'defense'),
        (Players, 'dexterity'),
        (Players, 'flee_rate'),
        (Players, 'poison_resistance'),
        (Players * NUM_MAGIC_ELEMENTAL, 'elemental_resistance'),
        (Players, 'unknown2'),
        (Players, 'unknown3'),
        (Players, 'unknown4'),
        (Players, 'covered_by'),
        (Players * MAX_PLAYER_MAGICS, 'magic'),
        (Players, 'walk_frames'),
        (Players, 'cooperative_magic'),
        (Players, 'unknown5'),
        (Players, 'unknown6'),
        (Players, 'death_sound'),
        (Players, 'attack_sound'),
        (Players, 'weapon_sound'),
        (Players, 'critical_sound'),
        (Players, 'magic_sound'),
        (Players, 'cover_sound'),
        (Players, 'dying_sound'),
    ]


class PoisonStatus(Structure):
    _fields_ = [
        ('H',             'poison_id'),
        ('H',             'poison_script')
    ]


class Inventory(Structure):
    _fields_ = [
        ('H',             'item'),
        ('H',             'amount'),
        ('H',             'amount_in_use')
    ]


class ObjectPlayer(Structure):
    _fields_ = [
        (WORD * 2, 'reserved'),
        ('H', 'script_on_friend_death'),
        ('H', 'script_on_dying')
    ]


class ObjectMagic(Structure):
    _fields_ = [
        ('H', 'magic_number'),
        ('H', 'reserved1'),
        ('H', 'script_on_success'),
        ('H', 'script_on_use'),
        ('H', 'reserved2'),
        ('H', 'flags'),
    ]
    if is_win95:
        _fields_.insert(-2, ('H', 'script_desc'))


class ObjectEnemy(Structure):
    _fields_ = [
        ('H', 'enemy_id'),
        ('H', 'resistance_to_sorcery'),
        ('H', 'script_on_turn_start'),
        ('H', 'script_on_battle_end'),
        ('H', 'script_on_ready'),
    ]


class ObjectPoison(Structure):
    _fields_ = [
        ('H', 'poison_level'),
        ('H', 'color'),
        ('H', 'player_script'),
        ('H', 'reserved'),
        ('H', 'enemy_script'),
    ]


class Obj(Structure):
    _fields_ = [
        (WORD * 7 if is_win95 else WORD * 6, 'data')]
    _opt_fields_ = [
        (ObjectPlayer, 'player'),
        (Item, 'item'),
        (ObjectMagic, 'magic'),
        (ObjectEnemy, 'enemy'),
        (ObjectPoison, 'poison')
    ]


EquipmentEffect = PlayerRoles * (MAX_PLAYER_EQUIPMENTS + 1)


class PlayerManagerMixin(object):
    def __init__(self):
        self.last_unequipped_item = None

    def add_poison_for_player(self, player_role, poison_id):
        index = 0
        while index < self.max_party_member_index + 1:
            if self.party[index].player_role == player_role:
                break
            index += 1
        if index > self.max_party_member_index:
            return
        i = 0
        while i < MAX_POISONS:
            w = self.poison_status[i][index].poison_id
            if w == 0:
                break
            if w == poison_id:
                return
            i += 1
        if i < MAX_POISONS:
            self.poison_status[i][index].poison_id = poison_id
            self.poison_status[i][index].poison_script = self.objects[poison_id].poison.player_script

    def cure_poison_by_kind(self, player_role, poison_id):
        index = 0
        while index < self.max_party_member_index + 1:
            if self.party[index].player_role == player_role:
                break
            index += 1
        if index > self.max_party_member_index:
            return
        for i in range(MAX_POISONS):
            if self.poison_status[i][index].poison_id == poison_id:
                self.poison_status[i][index].poison_id = 0
                self.poison_status[i][index].poison_script = 0

    def cure_poison_by_level(self, player_role, max_level):
        index = 0
        while index < self.max_party_member_index + 1:
            if self.party[index].player_role == player_role:
                break
            index += 1
        if index > self.max_party_member_index:
            return
        for i in range(MAX_POISONS):
            w = self.poison_status[i][index].poison_id
            if self.objects[w].poison.poison_level <= max_level:
                self.poison_status[i][index].poison_id = 0
                self.poison_status[i][index].poison_script = 0

    def is_player_poisoned_by_kind(self, player_role, poison_id):
        index = 0
        while index < self.max_party_member_index + 1:
            if self.party[index].player_role == player_role:
                break
            index += 1
        if index > self.max_party_member_index:
            return False
        for i in range(MAX_POISONS):
            if self.poison_status[i][index].poison_id == poison_id:
                return True
        return False

    def is_player_poisoned_by_level(self, player_role, min_level):
        index = 0
        while index < self.max_party_member_index + 1:
            if self.party[index].player_role == player_role:
                break
            index += 1
        if index > self.max_party_member_index:
            return False
        for i in range(MAX_POISONS):
            w = self.poison_status[i][index].poison_id
            w = self.objects[w].poison.poison_level
            if w >= 99:
                continue
            if w >= min_level:
                return True
        return False

    def add_magic(self, player_role, magic):
        for i in range(MAX_PLAYER_MAGICS):
            if self.player_roles.magic[i][player_role] == magic:
                return False
        i = 0
        while i < MAX_PLAYER_MAGICS:
            if self.player_roles.magic[i][player_role] == 0:
                break
            i += 1
        if i >= MAX_PLAYER_MAGICS:
            return False
        self.player_roles.magic[i][player_role] = magic
        return True

    def remove_magic(self, player_role, magic):
        for i in range(MAX_PLAYER_MAGICS):
            if self.player_roles.magic[i][player_role] == magic:
                self.player_roles.magic[i][player_role] = 0
                break

    def get_player_stat(self, player_role, name):
        w = getattr(self.player_roles, name)[player_role]
        for i in range(MAX_PLAYER_EQUIPMENTS + 1):
            w += getattr(self.equipment_effect[i], name)[player_role]
        w &= 0xFFFF
        return w

    get_player_attack_strength = partialmethod(get_player_stat, name='attack_strength')
    get_player_magic_strength = partialmethod(get_player_stat, name='magic_strength')
    get_player_defense = partialmethod(get_player_stat, name='defense')
    get_player_dexterity = partialmethod(get_player_stat, name='dexterity')
    get_player_flee_rate = partialmethod(get_player_stat, name='flee_rate')

    def get_player_poison_resistance(self, player_role):
        w = self.get_player_stat(player_role, 'poison_resistance')
        return min(w, 100)

    def get_player_elemental_resistance(self, player_role, attrib):
        w = self.player_roles.elemental_resistance[attrib][player_role]
        for i in range(MAX_PLAYER_EQUIPMENTS + 1):
            w += self.equipment_effect[i].elemental_resistance[attrib][player_role]
        w &= 0xFFFF
        return min(w, 100)

    def get_player_battle_sprite(self, player_role):
        w = self.player_roles.sprite_num_in_battle[player_role]
        for i in range(MAX_PLAYER_EQUIPMENTS + 1):
            if self.equipment_effect[i].sprite_num_in_battle[player_role] != 0:
                w = self.equipment_effect[i].sprite_num_in_battle[player_role]
        return w

    def get_player_cooperative_magic(self, player_role):
        w = self.player_roles.cooperative_magic[player_role]
        for i in range(MAX_PLAYER_EQUIPMENTS + 1):
            if self.equipment_effect[i].cooperative_magic[player_role] != 0:
                w = self.equipment_effect[i].cooperative_magic[player_role]
        return w

    def player_can_attack_all(self, player_role):
        f = False
        for i in range(MAX_PLAYER_EQUIPMENTS + 1):
            if self.equipment_effect[i].attack_all[player_role] != 0:
                f = True
                break
        return f

    def get_item_amount(self, item):
        for i in range(MAX_INVENTORY):
            if self.inventory[i].item == 0:
                break
            if self.inventory[i].item == item:
                return self.inventory[i].amount
        return 0

    def add_item_to_inventory(self, object_id, num):
        if object_id == 0:
            return False
        if num == 0:
            num = 1
        index = 0
        found = False
        while index < MAX_INVENTORY:
            if self.inventory[index].item == object_id:
                found = True
                break
            elif self.inventory[index].item == 0:
                break
            index += 1
        if num > 0:
            if index >= MAX_INVENTORY:
                return False
            if found:
                self.inventory[index].amount = min(
                    99, self.inventory[index].amount + num
                )
            else:
                self.inventory[index].item = object_id
                if num > 99:
                    num = 99
                self.inventory[index].amount = num
            return True
        else:
            if found:
                num = -num
                if self.inventory[index].amount < num:
                    self.inventory[index].amount = 0
                    return False
                self.inventory[index].amount -= num
                if (
                    self.inventory[index].amount == 0 and
                    index == self.cur_inv_menu_item and
                    index + 1 < MAX_INVENTORY and
                    self.inventory[index + 1].amount <= 0
                ):
                    self.cur_inv_menu_item -= 1
                return True
            return False

    def compress_inventory(self):
        j = 0
        for i in range(MAX_INVENTORY):
            # if self.inventory[i].item == 0:
            #     break
            if self.inventory[i].amount > 0:
                self.inventory[j] = self.inventory[i]
                j += 1
        for j in range(j, MAX_INVENTORY):
            self.inventory[j].amount = 0
            self.inventory[j].amount_in_use = 0
            self.inventory[j].item = 0

    def increase_hp_mp(self, player_role, hp, mp):
        success = False
        if self.player_roles.hp[player_role] > 0:
            player_hp = self.player_roles.hp[player_role]
            player_hp += hp
            if player_hp < 0:
                player_hp = 0
            elif player_hp > self.player_roles.max_hp[player_role]:
                player_hp = self.player_roles.max_hp[player_role]
            self.player_roles.hp[player_role] = player_hp
            player_mp = self.player_roles.mp[player_role]
            player_mp += mp
            if player_mp < 0:
                player_mp = 0
            elif player_mp > self.player_roles.max_mp[player_role]:
                player_mp = self.player_roles.max_mp[player_role]
            self.player_roles.mp[player_role] = player_mp
            success = True
        return success

    def update_equipments(self):
        self.equipment_effect = EquipmentEffect(None)
        for i in range(MAX_PLAYER_ROLES):
            for j in range(MAX_PLAYER_EQUIPMENTS):
                w = self.player_roles.equipment[j][i]
                if w != 0:
                    self.objects[w].item.script_on_equip = self.run_trigger_script(
                        self.objects[w].item.script_on_equip, i
                    )

    def remove_equipment_effect(self, player_role, equip_part):
        p = self.equipment_effect[equip_part]
        for i in range(0, PlayerRoles.struct_size, Players.struct_size):
            pack_into('H', p._buffer, i + player_role * 2, 0)
            p.__init__(p._buffer)
        if equip_part == BodyPart.Hand:
            self.player_status[player_role][Status.DualAttack] = 0
        elif equip_part == BodyPart.Wear:
            for i in range(self.max_party_member_index + 1):
                if self.party[i].player_role == player_role:
                    player_role = i
                    break
            else:
                return
            j = 0
            for i in range(MAX_POISONS):
                w = self.poison_status[i][player_role].poison_id
                if w == 0:
                    break
                if self.objects[w].poison.poison_level < 99:
                    self.poison_status[j][player_role] = self.poison_status[i][player_role]
                    j += 1
            while j < MAX_POISONS:
                self.poison_status[j][player_role].poison_id = 0
                self.poison_status[j][player_role].poison_script = 0
                j += 1

    def set_player_status(self, player_role, status_id, num_round):
        if status_id in {
            Status.Confused,
            Status.Sleep,
            Status.Silence,
            Status.Paralyzed
        }:
            if (
                self.player_roles.hp[player_role] != 0 and
                self.player_status[player_role][status_id] == 0
            ):
                self.player_status[player_role][status_id] = num_round
        elif status_id == Status.Puppet:
            if (
                self.player_roles.hp[player_role] == 0 and
                self.player_status[player_role][status_id] < num_round
            ):
                self.player_status[player_role][status_id] = num_round
        elif status_id in {
            Status.Bravery,
            Status.Protect,
            Status.DualAttack,
            Status.Haste
        }:
            if (
                self.player_roles.hp[player_role] != 0 and
                self.player_status[player_role][status_id] < num_round
            ):
                self.player_status[player_role][status_id] = num_round

    def remove_player_status(self, player_role, status_id):
        if self.player_status[player_role][status_id] <= 999:
            self.player_status[player_role][status_id] = 0

    def clear_all_player_status(self):
        for i in range(MAX_PLAYER_ROLES):
            for j in range(Status.All):
                if self.player_status[i][j] <= 999:
                    self.player_status[i][j] = 0

    def player_level_up(self, player_role, num_level):
        def stat_limit(group, player_role):
            if group[player_role] > 999:
                group[player_role] = 999

        self.player_roles.level[player_role] += num_level
        if self.player_roles.level[player_role] > MAX_LEVELS:
            self.player_roles.level[player_role] = MAX_LEVELS
        for i in range(num_level):
            self.player_roles.max_hp[player_role] += 10 + randint(0, 8)
            self.player_roles.max_mp[player_role] += 8 + randint(0, 6)
            self.player_roles.attack_strength[player_role] += 4 + randint(0, 1)
            self.player_roles.magic_strength[player_role] += 2 + randint(0, 1)
            self.player_roles.defense[player_role] += 2 + randint(0, 1)
            self.player_roles.dexterity[player_role] += 2 + randint(0, 1)
            self.player_roles.flee_rate[player_role] += 2
        attrs = [
            'max_hp',
            'max_mp',
            'attack_strength',
            'magic_strength',
            'defense',
            'dexterity',
            'flee_rate',
        ]
        for attr in attrs:
            stat_limit(getattr(self.player_roles, attr), player_role)
        self.exp.primary_exp[player_role].exp = 0
        self.exp.primary_exp[player_role].level = self.player_roles.level[player_role]
