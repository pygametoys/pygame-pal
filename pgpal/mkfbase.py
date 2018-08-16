#! /usr/bin/env python
# -*- coding: utf8 -*-
from struct import unpack_from
from pgpal.utils import singleton
from pgpal.compat import range, open_ignore_case as open


try:
    from pgpal._yj1 import YJ1Decoder
except ImportError:
    from pgpal.yj1 import YJ1Decoder
YJ1Decoder = singleton(YJ1Decoder)


class MKFDecoder(object):

    """
    MKF文件解码《仙剑》MKF文件的结构组成，以ABC.MKF为例：
    偏移         数据            含义
    00000000     6C 02 00 00     偏移表的长度，此值 / 4 - 2 = 包含文件个数
    00000004     6C 02 00 00     第1个子文件的偏移
    　     　                    第2-152个子件的偏移
    00000264     C2 6F 0F 00     第153个子文件的偏移
    00000268     64 9A 0F 00     此值指向文件末尾，也就是文件的长度
    0000026C     59 4A 5F 31     第1个子文件从这里开始，"YJ_1"是压缩文件的标志
    00000270     A0 08 00 00     这个值是文件的原始的长度
    00000274     12 07 00 00     这个值是文件压缩后的长度
    00000278     01 00           这个值是文件压缩占64K段的个数，通常为1
    0000027A     00 4A           这个值是数据压缩特征串表的长度
    0000027C     01 02 。。      从这开始是数据压缩特征串表
    000002C4     87 7B 02 4C     从这开始是压缩后的文件数据
    　     　                    其他压缩文件
    000F9A60     0B 12 80 38     文件的末尾
    """

    def __init__(self, path=None, data=None, yj1=True):
        # path和data不能同时是None
        assert path or data
        self.yj1 = YJ1Decoder() if yj1 else None
        try:
            # 优先使用path（优先从文件读取）
            if path:
                with open(path, 'rb') as f:
                    self._content = memoryview(f.read())
            else:
                self._content = memoryview(data)

            # 偏移（索引）表长度，假设文件前4位为6C 02 00 00（little-end的int值为
            # 26CH = 620），说明索引表长度为620字节，即620/4 = 155个整数，由于第一个
            # 整数被用于存储表长度，因此实际上只有后面154个整数存的是偏移量。另一方面，
            # 最后一个整数指向文件末尾，也就是文件的长度，因此实际上MKF内部的文件是由
            # 前后两个偏移量之间的byte表示的。这样由于一共有154个个偏移量，因此共有
            # 153个文件
            #
            # ！！！补充：第一个int（前四位）不仅是偏移表长度，也是第一个文件的开头
            # ABC.MKF中前面两个4位分别相等只是巧合（第一个文件为0）
            self.count = unpack_from('<I', self._content, 0)[0] // 4  # - 1
            self.indexes = tuple(
                unpack_from('<I', self._content, i << 2)[0]
                for i in range(self.count)
            )
            self.cache = [None] * self.count
            # 减去最后一个偏移量，对外而言，count就表示mkf文件中的子文件个数
            self.count -= 1
        except IOError:
            raise IOError('error occurs when try to open file ' + path)
        except TypeError:
            raise TypeError('data can not be converted to memoryview')

    def check(self, index):
        assert index in self

    def __contains__(self, index):
        return 0 <= index <= self.count

    def __len__(self):
        return self.count

    def is_yj1(self, index):
        """
        判断文件是否为YJ_1压缩
        """
        self.check(index)
        offset = self.indexes[index]
        return self._content[offset: offset + 4] == b'\x59\x4A\x5F\x31'

    def read(self, index, ref=False):
        """
        读取并返回指定文件，如果文件是经过YJ_1压缩的话，返回解压以后的内容
        """
        self.check(index + 1)
        if self.cache[index] is None:
            data = self._content[self.indexes[index]:self.indexes[index + 1]]
            if self.yj1 is not None and (self.is_yj1(index) or is_win95):
                data = memoryview(self.yj1.decode(data))
            self.cache[index] = data
        else:
            data = self.cache[index]
        if ref:
            return data.tobytes()
        else:
            if hasattr(data, 'tobytes') and not hasattr(data, 'cast'):
                return bytearray(data.tobytes())
            else:
                return data


def is_win_version():
    to_check = {'abc.mkf', 'map.mkf', 'f.mkf',
                'fbp.mkf', 'mgo.mkf', 'fire.mkf'}
    win_score = 0
    for name in to_check:
        try:
            mkf = MKFDecoder(name)
            if len(mkf):
                if any(mkf.is_yj1(i) for i in range(len(mkf))):
                    return False
                else:
                    win_score += 1
        except Exception:
            break
    return bool(win_score)


is_win95 = is_win_version()
