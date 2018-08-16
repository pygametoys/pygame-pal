# -*- coding: UTF-8 -*-
from enum import IntEnum
from pgpal.mkfbase import is_win95
from pgpal.compat import pg
from pgpal import config
from pygame.locals import *


DRAW_WIDTH = 320
DRAW_HEIGHT = 200
DRAW_PIXAL_WIDTH = 1
DRAW_PIXAL_HEIGHT = 1
REAL_WIDTH = 640
REAL_HEIGHT = 400


BITMAPNUM_SPLASH_UP = 0x03 if is_win95 else 0x26
BITMAPNUM_SPLASH_DOWN = 0x04 if is_win95 else 0x27
SPRITENUM_SPLASH_TITLE = 0x47
SPRITENUM_SPLASH_CRANE = 0x49
NUM_RIX_TITLE = 0x5


FRAME_TIME = 1000 // config['fps']
BATTLE_FRAME_TIME = 1000 // config['battle_fps']

MAX_PLAYERS_IN_PARTY = 3  # maximum number of players in party

MAX_PLAYER_ROLES = 6  # total number of possible player roles

MAX_PLAYABLE_PLAYER_ROLES = 5  # totally number of playable player roles

MAX_INVENTORY = 256  # maximum entries of inventory

MAX_STORE_ITEM = 9  # maximum items in a store

NUM_MAGIC_ELEMENTAL = 5  # total number of magic attributes

MAX_ENEMIES_IN_TEAM = 5  # maximum number of enemies in a team

MAX_PLAYER_EQUIPMENTS = 6  # maximum number of equipments for a player

MAX_PLAYER_MAGICS = 32  # maximum number of magics for a player

MAX_SCENES = 300  # maximum number of scenes

MAX_OBJECTS = 600  # maximum number of objects

# maximum number of event objects (should be somewhat more than the original
# as there are some modified versions which has more)
MAX_EVENT_OBJECTS = 5500

MAX_POISONS = 16  # maximum number of effective poisons to players

MAX_LEVELS = 99  # maximum number of level

MAX_SPRITE_TO_DRAW = 2048


class Status(IntEnum):
    # status of characters
    Confused = 0  # attack friends randomly
    Paralyzed = 1   # paralyzed
    Sleep = 2  # not allowed to move
    Silence = 3  # cannot use magic
    Puppet = 4  # for dead players only continue attacking
    Bravery = 5  # more power for physical attacks
    Protect = 6  # more defense value
    Haste = 7  # faster
    DualAttack = 8  # dual attack
    All = 9

    def __init__(self, val):
        self.val = val

    @property
    def word(self):
        return [
            0x1D,
            0x00,
            0x1C,
            0x1A,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ][self.val]

    @property
    def color(self):
        return [
            0x5F,
            0x00,
            0x0E,
            0x3C,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ][self.val]

    @property
    def pos(self):
        return [
            (35, 19),
            (0, 0),
            (54, 1),
            (55, 20),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
        ][self.val]


class BodyPart(IntEnum):
    # body parts of equipments
    Head = 0
    Body = 1
    Shoulder = 2
    Hand = 3
    Feet = 4
    Wear = 5
    Extra = 6


class ObjectState(IntEnum):
    # state of event object used by the sState field of the EVENTOBJECT struct
    Hidden = 0
    Normal = 1
    Blocker = 2


class TriggerMode(IntEnum):
    Null = 0
    SearchNear = 1
    SearchNormal = 2
    SearchFar = 3
    TouchNear = 4
    TouchNormal = 5
    TouchFar = 6
    TouchFarther = 7
    TouchFarthest = 8


class ItemFlag(IntEnum):
    Usable = (1 << 0)
    Equipable = (1 << 1)
    Throwable = (1 << 2)
    Consuming = (1 << 3)
    ApplyToAll = (1 << 4)
    Sellable = (1 << 5)
    EquipableByPlayerRole_First = (1 << 6)


class MagicFlag(IntEnum):
    UsableOutsideBattle = (1 << 0)
    UsableInBattle = (1 << 1)
    UsableToEnemy = (1 << 3)
    ApplyToAll = (1 << 4)


class MagicType(IntEnum):
    Normal = 0
    AttackAll = 1 # draw the effect on each of the enemies
    AttackWhole = 2 # draw the effect on the whole enemy team
    AttackField = 3 # draw the effect on the battle field
    ApplyToPlayer = 4 # the magic is used on one player
    ApplyToParty = 5 # the magic is used on the whole party
    Trance = 8 # trance the player
    Summon = 9 # summon


class Key(IntEnum):
    Null = 0
    Menu = (1 << 0)
    Search = (1 << 1)
    Down = (1 << 2)
    Left = (1 << 3)
    Up = (1 << 4)
    Right = (1 << 5)
    PgUp = (1 << 6)
    PgDn = (1 << 7)
    Repeat = (1 << 8)
    Auto = (1 << 9)
    Defend = (1 << 10)
    UseItem = (1 << 11)
    ThrowItem = (1 << 12)
    Flee = (1 << 13)
    Status = (1 << 14)
    Force = (1 << 15)
    Home = (1 << 16)
    End = (1 << 17)


keymap = {
    K_UP: Key.Up,
    K_KP8: Key.Up,
    K_DOWN: Key.Down,
    K_KP2: Key.Down,
    K_LEFT: Key.Left,
    K_KP4: Key.Left,
    K_RIGHT: Key.Right,
    K_KP6: Key.Right,
    K_ESCAPE: Key.Menu,
    K_INSERT: Key.Menu,
    K_LALT: Key.Menu,
    K_RALT: Key.Menu,
    K_KP0: Key.Menu,
    K_RETURN: Key.Search,
    K_SPACE: Key.Search,
    K_KP_ENTER: Key.Search,
    K_LCTRL: Key.Search,
    K_PAGEUP: Key.PgUp,
    K_KP9: Key.PgUp,
    K_PAGEDOWN: Key.PgDn,
    K_KP3: Key.PgDn,
    K_HOME: Key.Home,
    K_KP7: Key.Home,
    K_END: Key.End,
    K_KP1: Key.End,
    K_r: Key.Repeat,
    K_a: Key.Auto,
    K_d: Key.Defend,
    K_e: Key.UseItem,
    K_w: Key.ThrowItem,
    K_q: Key.Flee,
    K_f: Key.Force,
    K_s: Key.Status,
}


class Direction(IntEnum):
    South = 0
    West = 1
    North = 2
    East = 3
    Unknown = 4


dir_map = {
    Key.Up: Direction.North,
    Key.Down: Direction.South,
    Key.Left: Direction.West,
    Key.Right: Direction.East,
}


CHUNKNUM_SPRITEUI = 9

MAINMENU_BACKGROUND_FBPNUM = 2 if is_win95 else 60
RIX_NUM_OPENINGMENU = 4
MAINMENU_LABEL_NEWGAME = 7
MAINMENU_LABEL_LOADGAME = 8

LOADMENU_LABEL_SLOT_FIRST = 43

CONFIRMMENU_LABEL_NO = 19
CONFIRMMENU_LABEL_YES = 20

CASH_LABEL = 21

MENUITEM_COLOR = 0x4F
MENUITEM_COLOR_INACTIVE = 0x1C
MENUITEM_COLOR_CONFIRMED = 0x2C
MENUITEM_COLOR_SELECTED_INACTIVE = 0x1F
MENUITEM_COLOR_SELECTED_FIRST = 0xF9
MENUITEM_COLOR_SELECTED_TOTALNUM = 6
MENUITEM_COLOR_EQUIPPEDITEM = 0xC8

DESCTEXT_COLOR = 0x2E

SWITCHMENU_LABEL_DISABLE = 17
SWITCHMENU_LABEL_ENABLE = 18
GAMEMENU_LABEL_STATUS = 3
GAMEMENU_LABEL_MAGIC = 4
GAMEMENU_LABEL_INVENTORY = 5
GAMEMENU_LABEL_SYSTEM = 6
SYSMENU_LABEL_SAVE = 11
SYSMENU_LABEL_LOAD = 12
SYSMENU_LABEL_MUSIC = 13
SYSMENU_LABEL_SOUND = 14
SYSMENU_LABEL_QUIT = 15
SYSMENU_LABEL_BATTLEMODE = 606
SYSMENU_LABEL_LAUNCHSETTING = 612
BATTLESPEEDMENU_LABEL_1 = (SYSMENU_LABEL_BATTLEMODE + 1)
BATTLESPEEDMENU_LABEL_2 = (SYSMENU_LABEL_BATTLEMODE + 2)
BATTLESPEEDMENU_LABEL_3 = (SYSMENU_LABEL_BATTLEMODE + 3)
BATTLESPEEDMENU_LABEL_4 = (SYSMENU_LABEL_BATTLEMODE + 4)
BATTLESPEEDMENU_LABEL_5 = (SYSMENU_LABEL_BATTLEMODE + 5)
INVMENU_LABEL_USE = 23
INVMENU_LABEL_EQUIP = 22
STATUS_BACKGROUND_FBPNUM = 0
STATUS_LABEL_EXP = 2
STATUS_LABEL_LEVEL = 48
STATUS_LABEL_HP = 49
STATUS_LABEL_MP = 50
STATUS_LABEL_EXP_LAYOUT = 29
STATUS_LABEL_LEVEL_LAYOUT = 30
STATUS_LABEL_HP_LAYOUT = 31
STATUS_LABEL_MP_LAYOUT = 32
STATUS_LABEL_ATTACKPOWER = 51
STATUS_LABEL_MAGICPOWER = 52
STATUS_LABEL_RESISTANCE = 53
STATUS_LABEL_DEXTERITY = 54
STATUS_LABEL_FLEERATE = 55
STATUS_COLOR_EQUIPMENT = 0xBE
EQUIP_LABEL_HEAD = 600
EQUIP_LABEL_SHOULDER = 601
EQUIP_LABEL_BODY = 602
EQUIP_LABEL_HAND = 603
EQUIP_LABEL_FOOT = 604
EQUIP_LABEL_NECK = 605
BUYMENU_LABEL_CURRENT = 35
SELLMENU_LABEL_PRICE = 25
SPRITENUM_SLASH = 39
SPRITENUM_ITEMBOX = 70
SPRITENUM_CURSOR_YELLOW = 68
SPRITENUM_CURSOR = 69
SPRITENUM_PLAYERINFOBOX = 18
SPRITENUM_PLAYERFACE_FIRST = 48
EQUIPMENU_BACKGROUND_FBPNUM = 1
ITEMUSEMENU_COLOR_STATLABEL = 0xBB
BATTLEWIN_GETEXP_LABEL = 30
BATTLEWIN_BEATENEMY_LABEL = 9
BATTLEWIN_DOLLAR_LABEL = 10
BATTLEWIN_LEVELUP_LABEL = 32
BATTLEWIN_ADDMAGIC_LABEL = 33
BATTLEWIN_LEVELUP_LABEL_COLOR = 0xBB
SPRITENUM_ARROW = 47
BATTLE_LABEL_ESCAPEFAIL = 31

MENUITEM_VALUE_CANCELLED = 0xFFFF


class NumColor(IntEnum):
    Yellow = 1
    Blue = 2
    Cyan = 3


class NumAlign(IntEnum):
    Left = 1
    Mid = 2
    Right = 3


FONT_COLOR_DEFAULT = 0x4F
FONT_COLOR_YELLOW = 0x2D
FONT_COLOR_RED = 0x1A
FONT_COLOR_CYAN = 0x8D
FONT_COLOR_CYAN_ALT = 0x8C
FONT_COLOR_RED_ALT = 0x17

class DialogPos(IntEnum):
    Upper = 0
    Center = 1
    Lower = 2
    CenterWindow = 3


PAL_ADDITIONAL_WORD_FIRST = 10000


class LoadResFlag(IntEnum):
    Scene = 1 << 0
    PlayerSprite = 1 << 1


PAL_MAX_VOLUME = 100

MAX_ACTIONQUEUE_ITEMS = MAX_PLAYERS_IN_PARTY + MAX_ENEMIES_IN_TEAM * 2


class BattleUIState(IntEnum):
    Wait = 0
    SelectMove = 1
    SelectTargetEnemy = 2
    SelectTargetPlayer = 3
    SelectTargetEnemyAll = 4
    SelectTargetPlayerAll = 5


class BattleUIAction(IntEnum):
    Attack = 0
    Magic = 1
    CoopMagic = 2
    Misc = 3


class BattleMenuState(IntEnum):
    Main = 0
    MagicSelect = 1
    UseItemSelect = 2
    ThrowItemSelect = 3
    Misc = 4
    MiscItemSubMenu = 5


class BattleResult(IntEnum):
    Won = 3
    Lost = 1
    Fleed = 0xFFFF
    Terminated = 0
    OnGoing = 1000
    PreBattle = 1001
    Pause = 1002


class FighterState(IntEnum):
    Wait = 0
    Com = 1
    Act = 2


class BattleActionType(IntEnum):
    Pass = 0
    Defend = 1
    Attack = 2
    Magic = 3
    CoopMagic = 4
    Flee = 5
    ThrowItem = 6
    UseItem = 7
    AttackMate = 8


class BattlePhase(IntEnum):
    SelectAction = 0
    PerformAction = 1


SPRITENUM_BATTLEICON_ATTACK = 40
SPRITENUM_BATTLEICON_MAGIC = 41
SPRITENUM_BATTLEICON_COOPMAGIC = 42
SPRITENUM_BATTLEICON_MISCMENU = 43
SPRITENUM_BATTLE_ARROW_CURRENTPLAYER = 69
SPRITENUM_BATTLE_ARROW_CURRENTPLAYER_RED = 68
SPRITENUM_BATTLE_ARROW_SELECTEDPLAYER = 67
SPRITENUM_BATTLE_ARROW_SELECTEDPLAYER_RED = 66
BATTLEUI_LABEL_ITEM = 5
BATTLEUI_LABEL_DEFEND = 58
BATTLEUI_LABEL_AUTO = 56
BATTLEUI_LABEL_INVENTORY = 57
BATTLEUI_LABEL_FLEE = 59
BATTLEUI_LABEL_STATUS = 60
BATTLEUI_LABEL_USEITEM = 23
BATTLEUI_LABEL_THROWITEM = 24
TIMEMETER_COLOR_DEFAULT = 0x1B
TIMEMETER_COLOR_SLOW = 0x5B
TIMEMETER_COLOR_HASTE = 0x2A
BATTLEUI_MAX_SHOWNUM = 16
PAL_ITEM_DESC_BOTTOM = 1 << 15

ICON = b"""\
AAABAAEAQEAQAAEABABoCgAAFgAAACgAAABAAAAAgAAAAAEABAAAAAAAAAgAAAAAAAAAAAAAEAAA
ABAAAAAAAAAAAACAAACAAAAAgIAAgAAAAIAAgACAgAAAwMDAAICAgAAAAP8AAP8AAAD//wD/AAAA
/wD/AP//AAD///8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAzMzMzMzMzMzMzMzMzMzMzMzMzMzMAAAAAAAAAAAAAAAMzMzMzMzMzMzMzP//////
///////AAAAAAAAAAAAAAAzMzMzMzMzMzMzMz////////////8AAAAAAAAAAAAAAAMzMzMzMzMzM
zMzP/////////////AAAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAM
zMzMzMzMzMzMzP/////////////AAAAAAAAAAAAAAADMzMzMzMzMzMzMz////////////8AAAAAA
AAAAAAAAAMzMzMzMzMzMzMzP/////////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzMz/////////
///8AAAAAAAAAAAAAADMzMzMzMzMzMzMzP////////////zAAAAAAAAAAAAAAAzMzMzMzMzMzMzM
/////////////8AAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAMzMzM
zMzMzMzMzP/////////////MAAAAAAAAAAAAAAzMzMzMzMzMzMzM/////////////8wAAAAAAAAA
AAAADMzMzMzMzMzMzMzP/////////////AAAAAAAAAAAAAAMzMzMzMzMzMzMzM/////////////8
AAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzMzP////
/////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzM/////////////8AAAAAAAAAAAAAADMzMzMzMzM
zMzMz/////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzMzP/////////////AAAAAAAAAAAAAAA
DMzMzMzMzMzMzM/////////////8AAAAAAAAAAAAAAAMzMzMzMzMzMzMz/////////////wAAAAA
AAAAAAAAAAzMzMzMzMzMzMzP/////////////AAAAAAAAAAAAAAADMzMzMzMzMzMzM//////////
////wAAAAAAAAAAAAAAMzMzMzMzMzMzMz//////////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzM
/////////////8AAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAMzMzM
zMzMzMzMzP/////////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzM/////////////8AAAAAAAAAA
AAAADMzMzMzMzMzMzMzP////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzMzM/////////////M
AAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzMzP////
/////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzM/////////////8AAAAAAAAAAAAAADMzMzMzMzM
zMzMz//////////////AAAAAAAAAAAAAAMzMzMzMzMzMzMzM/////////////8AAAAAAAAAAAAAA
DMzMzMzMzMzMzMz//////////////AAAAAAAAAAAAAAMzMzMzMzMzMzMzP/////////////8AAAA
AAAAAAAAAADMzMzMzMzMzMzM//////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzMzP////////
/////8AAAAAAAAAAAAAADMzMzMzMzMzMzMz/////////////wAAAAAAAAAAAAAAMzMzMzMzMzMzM
zP/////////////AAAAAAAAAAAAAAAzMzMzMzMzMzMzM/////////////8AAAAAAAAAAAAAAAMzM
zMzMzMzMzMzP/////////////AwAAAAAAAAAAAAADMzMzMzMzMzMzMzMzMzMzMzMzMzMwMDAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AADMwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMzMAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAMzMzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAD/////////////////////////////////////////////////////////////////
/////////8AAAAAAD///4AAAAAAH///gAAAAAAf///AAAAAAA///+AAAAAAB///4AAAAAAH///wA
AAAAAf///AAAAAAA///8AAAAAAD///wAAAAAAH///gAAAAAAf//+AAAAAAB///4AAAAAAD///gAA
AAAAP//+AAAAAAA///4AAAAAAD///wAAAAAAP///AAAAAAA///8AAAAAAD///wAAAAAAP///AAAA
AAA///+AAAAAAD///4AAAAAAP///gAAAAAA///+AAAAAAB///4AAAAAAH///gAAAAAAf//+AAAAA
AB///4AAAAAAH///gAAAAAAf//+AAAAAAB///4AAAAAAD///wAAAAAAP///AAAAAAA///8AAAAAA
D///wAAAAAAH///AAAAAAAf//+AAAAAAA///4AAAAAAD///wAAAAAAP///AAAAAAAf//+AAAAAAB
///4AAAAAAH///gAAAAAAf///AAAAAAAv//+AAAAAABX/////////8f/////////x/////////+D
/////////4H/////////7///////////////////////////////////////////////////////
/////////w=="""


player_pos = [
    [(240, 170)],
    [(200, 176), (256, 152)],
    [(180, 180), (234, 170), (270, 146)]
]


def menuitem_color_selected():
    return MENUITEM_COLOR_SELECTED_FIRST + (pg.time.get_ticks() // 100) % MENUITEM_COLOR_SELECTED_TOTALNUM
