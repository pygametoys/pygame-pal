# -*- coding: utf8 -*-
from .compat import pg
from struct import pack, unpack
from ctypes import Structure
from . import dismkf
range = pg.compat.xrange_

mgo = dismkf.MGO()

class Walker:
    def __init__(me, manId):
        me.book = mgo[manId]
        me.cur = 0

    def getFrame(me):
        return me.book[me.cur]

class Actor(pg.sprite.Sprite):
    '''
    #name, paint
    '''
    def __init__(me, index=0, pos=(0, 0)):
        pg.sprite.Sprite.__init__(me)
        me.index = index
        me.tileId = 0
        me.path = 0
        me.pos = pos
        me.image = pg.Surface((0, 0))
        me.rect = me.image.get_rect()

    def load(me, frame):
        me.image = mgo[me.tileId][frame]
        me.rect = me.image.get_rect()
        
    def update(me):
        x, y = me.pos
        me.rect.left = x - me.image.get_width() / 2
        me.rect.bottom = y + 8


class OneExp:
    __slots__ = [
                'wExp',
                'wReserved',
                'wLevel',
                'wCount']
    def load(me, fin):
        for slot in me.__slots__:
            setattr(me, slot, unpack('H', fin.read(2)))

    def save(me, fout):
        for slot in me.__slots__:
            fout.write(pack('H', getattr(me, slot)))

class AllExp:
    __slots__ = [
            'PrimaryExp',
            'HealthExp',
            'MagicExp',
            'AttackExp',
            'MagicPowerExp',
            'DefenseExp',
            'DexterityExp',
            'FleeExp']
    def __init__(me):
        for slot in me.__slots__:
            setattr(me ,slot, [OneExp() for _ in range(6)])

    def load(me, fin):
        for slot in me.__slots__:
            getattr(me, slot).load(fin)

    def save(me, fout):
        for slot in me.__slots__:
            getattr(me, slot).save(fout)


class PartyMember:
    __slots__ =[
            'role'
            'x'
            'y'
            'frame'
            'offset'
            'tx'
            'ty'
            'td']

class Data:
    def __init__(me, num):
        me.num = num

    def load(me, fin):
        me.data = [unpack('H', fin.read(2)) for _ in range(me.num)]

    def save(me, fout):
        for data in me.data:
            fout.write(pack('H', data))

class PlayerRoles(Structure):
    def __init__(me):
        '''
        Avatar,
        SpriteNumInBattle,
        SpriteNum,
        Name,
        AttackAll,
        Unknown1,
        Level,
        MaxHP,
        MaxMP,
        HP,
        MP
        '''
        me.rgwEquipment = Data(6)
        me.rgwElementalResistance = Data(5)
        me.rgwMagic = Data(32)
        me.data1 = Data(11)
        me.data2 = Data(6)
        me.data3 = Data(4)
        me.data4 = Data(11)

    def load(me, fin):
        me.data1.load(fin)
        me.rgwEquipment.load(fin)
        me.data2.load(fin)
        me.rgwElementalResistance.load(fin)
        me.data3.load(fin)
        me.rgwMagic.load(fin)
        me.data4.load(fin)

    def save(me, fout):
        me.data1.save(fout)
        me.rgwEquipment.save(fout)
        me.data2.save(fout)
        me.rgwElementalResistance.save(fout)
        me.data3.save(fout)
        me.rgwMagic.save(fout)
        me.data4.save(fout)


class GameData:
    def __init__(me):
        me.members = [PartyMember() for _ in range(5)]

    def getInventoryCount(me):
        pass

    def findInventory(me, code):
        pass

    def addInventory(me, code, num):
        pass

    def saveData(me, fout):
        pass

    def loadData(me, fin):
        pass
