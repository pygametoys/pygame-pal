##! /usr/bin/env python
# -*- coding: UTF-8 -*-

# modified from huangcd's mkf.py
from collections import deque
from struct import unpack_from
from pgpal.compat import pg, range, partialmethod, lru_cache
from pgpal.utils import Object, pal_x, pal_y
from pgpal.mkfbase import MKFDecoder, YJ1Decoder


__all__ = ['RIX', 'Data', 'SSS', 'Ball', 'RGM',
           'GOPS', 'Fire', 'F', 'ABC', 'MGO', 'FBP',
           'RNG', 'MAP', 'calc_shadow_color']


@lru_cache(256)
def calc_shadow_color(source_color):
    return (source_color & 0xf0) | (source_color & 0x0f) >> 1


class RLEDecoder(Object):

    """
    RLE图片解析
    """
    def __init__(self, data):
        self.data = data

    @property
    def size(self):
        return self.width, self.height

    @property
    def width(self):
        return 0 if len(self.data) < 4 else unpack_from('H', self.data, 0)[0]

    @property
    def height(self):
        return 0 if len(self.data) < 4 else unpack_from('H', self.data, 2)[0]

    def blit_mono_color(self, dst_surface, pos, color_shift, color=None):
        pxarray = pg.PixelArray(dst_surface)
        max_w, max_h = dst_surface.get_size()
        ui_width, ui_height = self.size
        offset = 4

        i = 0
        if color is not None:
            color &= 0xF0
        while i < ui_width * ui_height:
            num = self.data[offset]
            offset += 1
            if (num & 0x80) and num <= 0x80 + ui_width:
                i += num - 0x80
            else:
                j = -1
                while j < num - 1:
                    j += 1
                    y = (i + j) // ui_width + pal_y(pos)
                    x = (i + j) % ui_width + pal_x(pos)
                    if x < 0:
                        j += -x - 1
                        continue
                    elif x >= max_w:
                        j += x - max_w
                        continue
                    if y < 0:
                        j += - y * ui_width - 1
                        continue
                    elif y >= max_h:
                        return
                    b = self.data[offset + j] & 0x0F
                    if b + color_shift > 0x0F:
                        b = 0x0F
                    elif b + color_shift < 0:
                        b = 0
                    else:
                        b += color_shift
                    if color is None:
                        pxarray[x, y] = b | (self.data[offset + j] & 0xF0)
                    else:
                        pxarray[x, y] = b | color
                offset += num
                i += num

    blit_with_color_shift = partialmethod(blit_mono_color, color=None)

    def blit_to_with_shadow(self, dst_surface, pos, shadow, pxarray=None):
        if pxarray is None:
            pxarray = pg.PixelArray(dst_surface)
        max_w, max_h = dst_surface.get_size()
        ui_width, ui_height = self.size
        if isinstance(pos, tuple):
            pos = pg.Rect(pos, self.size)
        offset = 4

        i = 0
        while i < ui_width * ui_height:
            num = self.data[offset]
            offset += 1
            if (num & 0x80) and num <= 0x80 + ui_width:
                i += num - 0x80
            else:
                y = i // ui_width + pos.y
                if y >= (pos.h + pos.y) or y >= max_h:
                    return
                elif y < 0:
                    j = - y * ui_width - 1
                    y = (i + j) // ui_width + pos.y
                    x = (i + j) % ui_width + pos.x
                else:
                    x = i % ui_width + pos.x
                if x < 0:
                    if num + x >= max(pos.x, 0) and pos.w + pos.x >= 0:
                        w = min(max_w, pos.w + pos.x, num + x)
                        pxarray[: w, y] = (
                            (calc_shadow_color(color) for color in pxarray[: w, y])
                            if shadow else
                            self.data[offset - x: offset - x + w]
                        )
                elif x <= max_w:
                    w = min(max_w - x, num)
                    pxarray[x: x + w, y] = (
                        (calc_shadow_color(color) for color in pxarray[x: x + w, y])
                        if shadow else
                        self.data[offset: offset + w]
                    )
                offset += num
                i += num

    blit_to = partialmethod(blit_to_with_shadow, shadow=False)


class RIX(MKFDecoder):

    def __init__(self):
        super(RIX, self).__init__('mus.mkf', yj1=False)


class SSS(MKFDecoder):
    def __init__(self):
        super(SSS, self).__init__('sss.mkf', yj1=False)


class SubPlace(MKFDecoder):

    """
    图元包，每个图元均为RLE，形状是菱形，而且其大小为32*15像素

    另外SubPlace里面不进行YJ_1的解码
    """

    def __init__(self, data):
        self.yj1 = YJ1Decoder()
        if len(data) < 2:
            self.count = 0
        else:
            self.count, = unpack_from('H', data, 0)
        self._content = memoryview(data)
        self.indexes = [
            (x << 1 if x != 0x18444 >> 1 else 0x18444 & 0xffff)
            if i < self.count else len(data) for i, x in
            enumerate(unpack_from('H' * (self.count + 1), self._content, 0))
        ]
        self.cache = [None] * self.count
        if self.indexes[-2] <= self.indexes[-3]:
            self.indexes = self.indexes[:-2] + self.indexes[-1:]
            self.count -= 1

    def is_yj1(self, index):
        return False

    def __getitem__(self, index):
        try:
            data = self.read(index)
            if isinstance(data, RLEDecoder):
                return data
            else:
                if len(data) >= 4 and data[:4] == b'\x02\x00\x00\x00':
                    data = data[4:]
                self.cache[index] = RLEDecoder(data)
                return self.cache[index]
        except AssertionError:
            return None


class GOPLike(Object):

    """
    类GOP.MKF的存储格式的mkf文件的解码器
    GOP文件结构：（gop.mkf)
    图元集，GOP属于子包结构，其中有226个图元包,其内每个图元均为RLE，形状是菱形，而且其大小为32*15像素
    """

    def __init__(self, path):
        self.data = {}
        self.mkf = MKFDecoder(path)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        elif 0 <= key <= self.mkf.count:
            data = self.mkf.read(key)
            if len(data):
                self[key] = SubPlace(data)
                return self[key]
            else:
                return None
        else:
            raise KeyError(key)

    def __setitem__(self, key, item):
        self.data[key] = item


class GOPS(GOPLike):

    """
    图元集，GOP属于子包结构，其中有226个图元包,其内每个图元均为RLE，形状是菱形，而且其大小为32*15像素
    （gop.mkf)
    """

    def __init__(self):
        super(GOPS, self).__init__('gop.mkf')


class Ball(SubPlace):

    """
    物品图片档，经过MKF解开后，每个子文件是标准的RLE图片（ball.mkf）
    """

    def __init__(self):
        MKFDecoder.__init__(self, 'ball.mkf', yj1=False)


class RGM(SubPlace):

    """
    人物头像档，经过MKF解开后，每个子文件是标准的RLE图片（RGM.mkf）
    """

    def __init__(self):
        MKFDecoder.__init__(self, 'rgm.mkf', yj1=False)


class Fire(GOPLike):

    """
    法术效果图，同GOP有着同样的存储方式，但图元包经过YJ_1压缩（FIRE.mkf）
    """

    def __init__(self):
        super(Fire, self).__init__('fire.mkf')


class F(GOPLike):

    """
    我战斗形象，同GOP有着同样的存储方式，但图元包经过YJ_1压缩（F.mkf）
    """

    def __init__(self):
        super(F, self).__init__('f.mkf')


class ABC(GOPLike):

    """
    敌战斗形象，同GOP有着同样的存储方式，但图元包经过YJ_1压缩（ABC.mkf）
    """

    def __init__(self):
        super(ABC, self).__init__('abc.mkf')


class MGO(GOPLike):

    """
    各种人物形象，同GOP有着同样的存储方式，但图元包经过YJ_1压缩（MGO.mkf）
    """

    def __init__(self):
        super(MGO, self).__init__('mgo.mkf')


class Data(MKFDecoder):
    def __init__(self):
        super(Data, self).__init__('data.mkf', yj1=False)


class FBP(MKFDecoder):

    """
    背景图，经过MKF解开后，每个子文件必须经过DEYJ1解压，
    解开后的大小是64000字节，用来描述战斗时的背景（320*200），
    其数据是调色板的索引。（FBP.mkf）
    """

    def __init__(self):
        super(FBP, self).__init__('fbp.mkf')

    def render(self, index, surface):
        width, height = 320, 200
        pxarray = pg.PixelArray(surface)
        try:
            data = self.read(index)
            for y in range(height):
                for x in range(width):
                    pxarray[x, y] = data[x + y * width]
        except AssertionError:
            pass
        del pxarray
        surface.unlock()


class RNG(MKFDecoder):

    """
    过场动画（RNG.mkf）
    RNG文件经过MKF解开后，每个子文件仍然是一个经过MKF压缩的文件，
    然后再次经过MKF解开后，其子文件是一个YJ1压缩的文件（够复杂吧，
    大量的解压缩需要高的CPU资源，仙剑在386时代就能很好的完成，呵呵，厉害）。

    以第一次解开的MKF文件为例子，假如该文件为1.RNG，
    对该文件再次进行MKF解压后，会得到若干个小的文件
    （1_01，1_02，1_03……），这些小文件中（需要再次经过DEYJ1解压），
    第一个文件通过比较大，而其后的文件比较小，这是由于其第一个文件是描述动画的第一帧，
    而以后的文件只描述在第一帧上进行变化的数据。

    在描述变化信息的文件中，由于不包含变化位置的坐标信息，
    因此也总是从动画位置的左上角（0，0）开始的，依次描述变化，
    直至无变化可描述以止则结束（因此如果当前帧和前一帧变化较大，
    则描述文件会比较大）。

    RNG图片也是320×200的
    """

    def __init__(self):
        super(RNG, self).__init__('rng.mkf', yj1=False)

    def start_video(self, index, surface):
        """
        开始一段录像，返回录像的帧数
        """
        videodata = self.read(index)
        self.video = MKFDecoder(data=videodata)
        self.frame_index = 0
        self.image = surface
        self.pxarray = pg.PixelArray(self.image)
        return len(self.video)

    def finish_current_video(self):
        del self.pxarray
        del self.video
        del self.frame_index
        del self.image

    def has_next_frame(self):
        return self.frame_index < self.video.count

    def read_byte(self):
        return self.data.popleft()

    def read_short(self):
        return self.data.popleft() | (self.data.popleft() << 8)

    def set_byte(self, color=None):
        y, x = divmod(self.dst_ptr, 320)
        color = self.read_byte() if color is None else color
        self.pxarray[x, y] = color
        self.dst_ptr += 1

    def render(self):
        """
        解开帧动画
        @param data: 字符串形式的数据
        """
        self.dst_ptr = 0
        bdata = wdata = ddata = 0

        while True:
            bdata = self.read_byte()
            if bdata in {0x00, 0x13} or not len(self.data):
                return
            elif bdata == 0x02:
                self.dst_ptr += 2
            elif bdata == 0x03:
                bdata = self.read_byte()
                self.dst_ptr += (bdata + 1) << 1
            elif bdata == 0x04:
                wdata = self.read_short()
                self.dst_ptr += (wdata + 1) << 1
            elif 0x06 <= bdata <= 0x0a:
                for _ in range(bdata, 0x05, -1):
                    self.set_byte()
                    self.set_byte()
            elif bdata == 0x0b:
                bdata = self.read_byte()
                for _ in range(bdata + 1):
                    self.set_byte()
                    self.set_byte()
            elif bdata == 0x0c:
                ddata = self.read_short()
                for _ in range(ddata + 1):
                    self.set_byte()
                    self.set_byte()
            elif 0x0d <= bdata <= 0x10:
                color1, color2 = self.read_byte(), self.read_byte()
                for _ in range(bdata - 0x0b):
                    self.set_byte(color1)
                    self.set_byte(color2)
            elif bdata == 0x11:
                bdata = self.read_byte()
                color1, color2 = self.read_byte(), self.read_byte()
                for _ in range(bdata + 1):
                    self.set_byte(color1)
                    self.set_byte(color2)
            elif bdata == 0x12:
                ddata = self.read_short()
                color1, color2 = self.read_byte(), self.read_byte()
                for _ in range(ddata + 1):
                    self.set_byte(color1)
                    self.set_byte(color2)

    def get_next_frame(self):
        """
        @member data: 两次MKFDecoder加上YJ_1Decoder解析之后得到的帧信息（字符串）
        @member info: self.data经过blit处理以后的数据（Byte数组）
        """
        self.data = deque(self.video.read(self.frame_index))

        if self.data:
            self.render()
            self.image.unlock()
        if self.has_next_frame():
            self.frame_index += 1
        return self.image


class MAP(MKFDecoder):
    """
    地图档（MAP.mkf）

    MAP和GOP有着相同的子文件数，因此，MAP和GOP是一一对应的关系。
    MAP经过MKF解开后，其子文件采用DEYJ1方式压缩。经过DEYJ1解开后
    的文件都应该具有65536字节的大小，其具体格式如下：

    每512字节描述一行，共有128行（512*128=65536字节）。其中第一
    行中，每4个字节描述一个图元。这 4个字节中，头两个字节用来描
    述底层图片的索引，后两字节描述在该底层图片上覆盖图片的信息。
    其中图片在GOP中的索引的计算为：将高位字节的第5位移到低位字节
    的前面，形成一个9字节描述的索引，如下面的代码：

    fel = read_byte(); //低字节
    felp = read_byte(); //高字节
    felp >>= 4;
    felp &= 1; //取高字节的第5位的值
    elem1 = ( felp << 8) | fel; //图元在GOP中的索引

    对于覆盖层信息，索引的计算方式同上，只不过仅当索引大于0的时
    候才进行覆盖（因此并非所有地方都需要覆盖），并且覆盖的索引需
    要减去1才是覆盖层在GOP中的真正索引。

    另外需要注意的是，在同一行中，第偶数张图片的上角会与前一张图
    片的右角进行拼接，因此其显示位置为前一张图片的(x+16, y+8)的地
    方，以下是示例：

    第一行：(0, 0)(16, 8)(32, 0)(48, 8)(64, 0)......
    第二行：(0, 16)(16, 24)(32, 16)(48, 24)(64, 16)......

    地图大小是2064×2064
    """
    def __init__(self):
        self.index = -1
        super(MAP, self).__init__('map.mkf')

    def load(self, index, gop):
        if self.index != index:
            data = self.read(index)
            if len(data):
                self.tiles = tuple(
                    tuple(
                        tuple(
                            unpack_from(
                                'I', data, (y << 9) + (x << 3) + (h << 2)
                            )[0] for h in range(2)
                        ) for x in range(64)
                    ) for y in range(128)
                )
                self.sub_place = gop[index]
                self.index = index

    def get_tile_bitmap(self, x, y, h, layer):
        if x >= 64 or y >= 128 or h > 1:
            return None
        else:
            d = self.tiles[y][x][h]
            if layer:
                d >>= 16
                return self.sub_place[((d & 0xFF) | ((d >> 4) & 0x100)) - 1]
            else:
                return self.sub_place[(d & 0xFF) | ((d >> 4) & 0x100)]

    def get_tile_height(self, x, y, h, layer):
        if x >= 64 or y >= 128 or h > 1:
            return 0
        else:
            d = self.tiles[y][x][h]
            if layer:
                d >>= 16
            d >>= 8
            return d & 0xf

    def tile_blocked(self, x, y, h):
        if x >= 64 or y >= 128 or h > 1:
            return True
        else:
            return (self.tiles[y][x][h] & 0x2000) >> 13

    def blit_to(self, surface, rect, layer):
        pxarray = pg.PixelArray(surface)
        dst_rect = surface.get_rect().inflate(32, 16)
        sy = rect.y // 16 - 1
        sx = rect.x // 32 - 1
        dy = (rect.y + rect.h) // 16 + 2
        dx = (rect.x + rect.w) // 32 + 2

        y_pos = sy * 16 - 8 - rect.y
        for y in range(sy, dy):
            for h in range(2):
                x_pos = sx * 32 + h * 16 - 16 - rect.x
                for x in range(sx, dx):
                    if dst_rect.collidepoint(x_pos, y_pos):
                        bitmap = self.get_tile_bitmap(x, y, h, layer)
                        if bitmap is None:
                            if layer:
                                continue
                            bitmap = self.get_tile_bitmap(0, 0, 0, layer)
                        bitmap.blit_to(surface, (x_pos, y_pos), pxarray=pxarray)
                    x_pos += 32
                y_pos += 8
