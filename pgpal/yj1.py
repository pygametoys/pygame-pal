#! /usr/bin/env python
# -*- coding: utf8 -*-
import attr
from struct import unpack_from
from array import array
from pgpal.compat import range, zip
from pgpal.utils import Structure, Pointer


@attr.s
class YJ1_TreeNode(object):
    value = attr.ib(default=0)
    weight = attr.ib(default=1)
    leaf = attr.ib(default=None)
    left = attr.ib(default=None)
    right = attr.ib(default=None)


class YJ_1_FileHeader(Structure):
    _fields_ = [
        ('I', 'Signature'),
        ('I', 'UncompressedLength'),
        ('I', 'CompressedLength'),
        ('H', 'BlockCount'),
        ('B', 'Unknown'),
        ('B', 'HuffmanTreeLength'),
    ]


class YJ_1_BlockHeader(Structure):
    _fields_ = [
        ('H', 'UncompressedLength'),
        ('H', 'CompressedLength'),
        ('4H', 'LZSSRepeatTable'),
        ('4B', 'LZSSOffsetCodeLengthTable'),
        ('3B', 'LZSSRepeatCodeLengthTable'),
        ('3B', 'CodeCountCodeLengthTable'),
        ('2B', 'CodeCountTable'),
    ] 


@attr.s
class YJ2_TreeNode(object):
    value = attr.ib()
    weight = attr.ib(default=1)
    parent = attr.ib(default=None)
    left = attr.ib(default=None)
    right = attr.ib(default=None)


@attr.s
class YJ2_Tree(object):
    _list = attr.ib(default=None)
    node = attr.ib(default=None)


yj2_data1 = array('B', (
    0x3f, 0x0b, 0x17, 0x03, 0x2f, 0x0a, 0x16, 0x00, 0x2e, 0x09, 0x15, 0x02, 0x2d, 0x01, 0x08, 0x00,
    0x3e, 0x07, 0x14, 0x03, 0x2c, 0x06, 0x13, 0x00, 0x2b, 0x05, 0x12, 0x02, 0x2a, 0x01, 0x04, 0x00,
    0x3d, 0x0b, 0x11, 0x03, 0x29, 0x0a, 0x10, 0x00, 0x28, 0x09, 0x0f, 0x02, 0x27, 0x01, 0x08, 0x00,
    0x3c, 0x07, 0x0e, 0x03, 0x26, 0x06, 0x0d, 0x00, 0x25, 0x05, 0x0c, 0x02, 0x24, 0x01, 0x04, 0x00,
    0x3b, 0x0b, 0x17, 0x03, 0x23, 0x0a, 0x16, 0x00, 0x22, 0x09, 0x15, 0x02, 0x21, 0x01, 0x08, 0x00,
    0x3a, 0x07, 0x14, 0x03, 0x20, 0x06, 0x13, 0x00, 0x1f, 0x05, 0x12, 0x02, 0x1e, 0x01, 0x04, 0x00,
    0x39, 0x0b, 0x11, 0x03, 0x1d, 0x0a, 0x10, 0x00, 0x1c, 0x09, 0x0f, 0x02, 0x1b, 0x01, 0x08, 0x00,
    0x38, 0x07, 0x0e, 0x03, 0x1a, 0x06, 0x0d, 0x00, 0x19, 0x05, 0x0c, 0x02, 0x18, 0x01, 0x04, 0x00,
    0x37, 0x0b, 0x17, 0x03, 0x2f, 0x0a, 0x16, 0x00, 0x2e, 0x09, 0x15, 0x02, 0x2d, 0x01, 0x08, 0x00,
    0x36, 0x07, 0x14, 0x03, 0x2c, 0x06, 0x13, 0x00, 0x2b, 0x05, 0x12, 0x02, 0x2a, 0x01, 0x04, 0x00,
    0x35, 0x0b, 0x11, 0x03, 0x29, 0x0a, 0x10, 0x00, 0x28, 0x09, 0x0f, 0x02, 0x27, 0x01, 0x08, 0x00,
    0x34, 0x07, 0x0e, 0x03, 0x26, 0x06, 0x0d, 0x00, 0x25, 0x05, 0x0c, 0x02, 0x24, 0x01, 0x04, 0x00,
    0x33, 0x0b, 0x17, 0x03, 0x23, 0x0a, 0x16, 0x00, 0x22, 0x09, 0x15, 0x02, 0x21, 0x01, 0x08, 0x00,
    0x32, 0x07, 0x14, 0x03, 0x20, 0x06, 0x13, 0x00, 0x1f, 0x05, 0x12, 0x02, 0x1e, 0x01, 0x04, 0x00,
    0x31, 0x0b, 0x11, 0x03, 0x1d, 0x0a, 0x10, 0x00, 0x1c, 0x09, 0x0f, 0x02, 0x1b, 0x01, 0x08, 0x00,
    0x30, 0x07, 0x0e, 0x03, 0x1a, 0x06, 0x0d, 0x00, 0x19, 0x05, 0x0c, 0x02, 0x18, 0x01, 0x04, 0x00
))


yj2_data2 = array('B', (
    0x08, 0x05, 0x06, 0x04, 0x07, 0x05, 0x06, 0x03, 0x07, 0x05, 0x06, 0x04, 0x07, 0x04, 0x05, 0x03
))


class YJ1Decoder(object):

    def decode(self, _data):
        data = bytearray(_data)
        if not len(data):
            return memoryview(data)
        if data[:4] == b'\x59\x4A\x5F\x31':
            org_len, = unpack_from('I', data, 4)
        else:
            org_len, = unpack_from('I', data)
        if data[:4] == b'\x59\x4A\x5F\x31':
            decompress = self.yj1_decompress
        elif len(data) * 100 < org_len:
            return _data
        else:
            decompress = yj2_decompress
        dest = bytearray(org_len)

        dst_len = decompress(data, dest, org_len)

        if org_len == dst_len:
            return memoryview(dest)
        else:
            return _data

    def yj1_get_bits(self, src, count):
        temp = src + ((self.bitptr >> 4) << 1)
        bptr = self.bitptr & 0xf
        self.bitptr += count
        if count > 16 - bptr:
            count += bptr - 16
            mask = 0xffff >> bptr
            return (
                ((temp[0] | (temp[1] << 8)) & mask) << count
            ) | ((temp[2] | (temp[3] << 8)) >> (16 - count))
        else:
            return (
                (((temp[0] | (temp[1] << 8)) << bptr) & 0xffff) >> (16 - count)
            )

    def yj1_get_loop(self, src, header):
        if self.yj1_get_bits(src, 1):
            return header.CodeCountTable[0]
        else:
            temp = self.yj1_get_bits(src, 2)
            if temp:
                return self.yj1_get_bits(src, header.CodeCountCodeLengthTable[temp - 1])
            else:
                return header.CodeCountTable[1]

    def yj1_get_count(self, src, header):
        temp = self.yj1_get_bits(src, 2)
        if temp != 0:
            if self.yj1_get_bits(src, 1):
                return self.yj1_get_bits(src, header.LZSSRepeatCodeLengthTable[temp - 1])
            else:
                return header.LZSSRepeatTable[temp]
        else:
            return header.LZSSRepeatTable[0]

    def yj1_decompress(self, source, dst, dst_size):
        hdr = YJ_1_FileHeader(source)
        src = Pointer(source, 0)
        dest = 0
        if not len(src):
            return -1
        if hdr.Signature != 0x315f4a59:
            return -1
        if hdr.UncompressedLength > dst_size:
            return -1

        tree_len = hdr.HuffmanTreeLength * 2
        self.bitptr = 0
        flag = Pointer(src, 16 + tree_len)
        root = [YJ1_TreeNode() for _ in range(tree_len + 1)]
        root[0].leaf = 0
        root[0].value = 0
        root[0].left = Pointer(root, 1)
        root[0].right = Pointer(root, 2)
        for i in range(1, tree_len + 1):
            root[i].leaf = not self.yj1_get_bits(flag, 1)
            root[i].value = src[15 + i]
            if root[i].leaf:
                root[i].left = root[i].right = None
            else:
                root[i].left = Pointer(root, (root[i].value << 1) + 1)
                root[i].right = root[i].left + 1
        src += 16 + tree_len + ((
            (tree_len >> 4) + 1 if tree_len & 0xf else (tree_len >> 4)
        ) << 1)

        for i in range(hdr.BlockCount):
            pre_src = src
            header = YJ_1_BlockHeader(src[0:])
            src += 4

            if not header.CompressedLength:
                hul = header.UncompressedLength
                while hul:
                    dst[dest] = src[0]
                    dest += 1
                    src += 1
                    hul -= 1
                continue
            src += 20
            self.bitptr = 0

            while True:
                loop = self.yj1_get_loop(src, header)
                if loop == 0:
                    break
                while loop:
                    node = Pointer(root, 0)
                    while not node[0].leaf:
                        if self.yj1_get_bits(src, 1):
                            node = node[0].right
                        else:
                            node = node[0].left
                    dst[dest] = node[0].value
                    dest += 1
                    loop -= 1
                loop = self.yj1_get_loop(src, header)
                if loop == 0:
                    break
                while loop:
                    count = self.yj1_get_count(src, header)
                    pos = self.yj1_get_bits(src, 2)
                    pos = self.yj1_get_bits(src, header.LZSSOffsetCodeLengthTable[pos])
                    while count:
                        dst[dest] = dst[dest - pos]
                        dest += 1
                        count -= 1
                    loop -= 1
            src = pre_src + header.CompressedLength

        return hdr.UncompressedLength


def yj2_adjust_tree(tree, value):
    root = tree._list
    node = root[value]
    while node[0].value != 0x280:
        temp = node + 1
        while node[0].weight == temp[0].weight:
            temp += 1
        temp -= 1
        if temp != node:
            node[0].parent, temp[0].parent = temp[0].parent, node[0].parent
            if node[0].value > 0x140:
                node[0].left[0].parent = temp
                node[0].right[0].parent = temp
            else:
                root[node[0].value] = temp
            if temp[0].value > 0x140:
                temp[0].left[0].parent = node
                temp[0].right[0].parent = node
            else:
                root[temp[0].value] = node
            node[0], temp[0] = temp[0], node[0]
            node = temp
        node[0].weight += 1
        node = node[0].parent
    node[0].weight += 1


def yj2_build_tree(tree):
    tree.node = [YJ2_TreeNode(i) for i in range(641)]
    tree._list = [Pointer(tree.node, i) for i in range(321)]
    tree.node[0x280].parent = Pointer(tree.node, 0x280)
    for i, ptr in zip(range(0, 0x280, 2), range(0x141, 0x281)):
        tree.node[ptr].left = Pointer(tree.node, i)
        tree.node[ptr].right = Pointer(tree.node, i + 1)
        tree.node[i].parent = tree.node[i + 1].parent = Pointer(tree.node, ptr)
        tree.node[ptr].weight = tree.node[i].weight + tree.node[i + 1].weight
    return True


def yj2_bt(data, pos):
    return (data[pos >> 3] & ((1 << (pos & 0x7)) & 0xff)) >> (pos & 0x7)


def yj2_decompress(source, dst, dst_size):
    ptr = 0
    tree = YJ2_Tree()
    src = source[4:]
    dest = 0
    if not source or not yj2_build_tree(tree):
        return -1
    length, = unpack_from('I', source)
    if length > dst_size:
        return -1
    while True:
        node = Pointer(tree.node, 0x280)
        while node[0].value > 0x140:
            if yj2_bt(src, ptr):
                node = node[0].right
            else:
                node = node[0].left
            ptr += 1
        val = node[0].value
        if tree.node[0x280].weight == 0x8000:
            for i in range(0x141):
                if tree._list[i][0].weight & 0x1:
                    yj2_adjust_tree(tree, i)
            for node in tree.node:
                node.weight >>= 1
        yj2_adjust_tree(tree, val)
        if val > 0xff:
            temp = 0
            for i in range(8):
                temp |= yj2_bt(src, ptr) << i
                ptr += 1
            tmp = temp & 0xff
            for i in range(8, yj2_data2[tmp & 0xf] + 6):
                temp |= yj2_bt(src, ptr) << i
                ptr += 1
            temp >>= yj2_data2[tmp & 0xf]
            pos = (temp & 0x3f) | (yj2_data1[tmp] << 6)
            if pos == 0xfff:
                break
            pre = dest - pos - 1
            for _ in range(val - 0xfd):
                dst[dest] = dst[pre]
                dest += 1
                pre += 1
        else:
            dst[dest] = val
            dest += 1
    return length
