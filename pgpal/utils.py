#! /usr/bin/env python
# -*- coding: utf8 -*-
import sys
import struct
from operator import itemgetter
import attr
from six import add_metaclass, reraise
import wrapt
from pgpal.compat import range


@attr.s
class Pointer(object):
    obj = attr.ib()
    start = attr.ib(default=0)

    def __len__(self):
        return max(len(self.obj) - self.start, 0)

    def __add__(self, offset):
        return Pointer(self.obj, self.start + offset)

    def __sub__(self, offset):
        return Pointer(self.obj, self.start - offset)

    def __getitem__(self, offset):
        if isinstance(offset, int):
            return self.obj[self.start + offset]
        elif isinstance(offset, slice):
            new_slice = slice(
                self.start if offset.start is None else self.start + offset.start,
                offset.stop if offset.stop is None else self.start + offset.stop,
                offset.step
            )
            return self.obj[new_slice]

    def __setitem__(self, offset, val):
        self.obj[self.start + offset] = val


class StructField(object):
    '''
    Descriptor representing a simple structure field
    '''
    def __init__(self, format, offset):
        self.format = format
        self.offset = offset

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            r = struct.unpack_from(self.format, instance._buffer, self.offset)
            return r[0] if len(r) == 1 else r

    def __set__(self, instance, val):
        try:
            struct.pack_into(self.format, instance._buffer, self.offset, val)
        except struct.error:
            if len(self.format) == 1 and self.format in 'bBhHiIlLqQ':
                _struct = struct.Struct(self.format)
                size = _struct.size
                base = int(b'0x' + size * b'ff', 16)
                if self.format.islower():
                    base = (base + 1) // 2
                    val = (val % base) - (val & base)
                else:
                    val = val & base
                _struct.pack_into(instance._buffer, self.offset, val)
            else:
                reraise(*sys.exc_info())

    def __mul__(self, other):
        if isinstance(other, int):
            return StructureMeta(self.format + '_' + str(other), (Structure, ), {
                '_fields_': [
                    (self.format, i)
                    for i in range(other)
                ]
            })
        else:
            raise NotImplementedError('unsupported operand type(s) for *: %s and %s' % (
                repr(type(self).__name__), repr(type(other).__name__)))


class NestedStruct(object):
    '''
    Descriptor representing a nested structure
    '''
    def __init__(self, name, struct_type, offset):
        self.name = name
        self.struct_type = struct_type
        self.offset = offset

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            data = instance._buffer[
                self.offset:self.offset+self.struct_type.struct_size
            ]
            result = self.struct_type(data)
            return result

    def __set__(self, instance, val):
        size = self.struct_type.struct_size
        if size == val.struct_size:
            instance._buffer[self.offset:self.offset+size] = val._buffer


class StructureMeta(type):
    '''
    Metaclass that automatically creates StructField descriptors,
    Modified from Python Cookbook 3rd edition
    '''
    def __init__(self, clsname, bases, clsdict):
        def getitem(self, index):
            if type(index) is int:
                return getattr(self, str(index))
            elif isinstance(index, int):
                return getattr(self, str(int(index)))
            elif isinstance(index, slice):
                pass
            else:
                raise AttributeError('%s instance has no attribute %s' % (
                    repr(type(self).__name__), repr(index)))

        def setitem(self, index, val):
            if type(index) is int:
                return setattr(self, str(index), val)
            elif isinstance(index, int):
                return setattr(self, str(int(index)), val)
            elif isinstance(index, slice):
                pass
            else:
                raise AttributeError('%s instance has no attribute %s' % (
                    repr(type(self).__name__), repr(index)))
        fields = getattr(self, '_fields_', [])
        byte_order = ''
        offset = 0
        for format, fieldname in fields:
            fieldname = str(fieldname)
            if isinstance(format, StructureMeta):
                setattr(self, fieldname,
                        NestedStruct(fieldname, format, offset))
                offset += format.struct_size
            elif isinstance(format, StructField):
                fmt = format.format
                format.offset = offset
                setattr(self, fieldname, format)
                offset += struct.calcsize(fmt)
            else:
                if format.startswith(('<', '>', '!', '@')):
                    byte_order = format[0]
                    format = format[1:]
                format = byte_order + format
                setattr(self, fieldname, StructField(format, offset))
                offset += struct.calcsize(format)
        if all(isinstance(fieldname, int) for format, fieldname in fields):
            setattr(self, '__getitem__', getitem)
            setattr(self, '__setitem__', setitem)
        setattr(self, 'struct_size', offset)

    def __mul__(self, other):
        if isinstance(other, int):
            return StructureMeta(self.__name__ + '_' + str(other), (Structure,), {
                '_fields_': [
                    (self, i)
                    for i in range(other)
                ]
            })
        else:
            raise NotImplementedError('unsupported operand type(s) for *: %s and %s' % (
                repr(type(self).__name__), repr(type(other).__name__)))


class Union(StructureMeta):
    def __init__(self, clsname, bases, clsdict):
        StructureMeta.__init__(self, clsname, bases, clsdict)
        opt_fields = getattr(self, '_opt_fields_', [])
        byte_order = ''
        offset = 0
        for format, fieldname in opt_fields:
            fieldname = str(fieldname)
            if isinstance(format, StructureMeta):
                setattr(self, fieldname,
                        NestedStruct(fieldname, format, offset))
            elif isinstance(format, StructField):
                format.offset = offset
                setattr(self, fieldname, format)
            else:
                if format.startswith(('<', '>', '!', '@')):
                    byte_order = format[0]
                    format = format[1:]
                format = byte_order + format
                setattr(self, fieldname, StructField(format, offset))


@add_metaclass(Union)
class Structure(object):
    '''
    A simple fixed size struct implementation just like ctypes.Structure
    '''

    def __init__(self, bytedata):
        if bytedata is None:
            bytedata = b'\x00' * self.struct_size
        if isinstance(bytedata, memoryview):
            self._buffer = bytedata[:self.struct_size]
        else:
            self._buffer = memoryview(bytearray(bytedata[:self.struct_size]))

    @classmethod
    def from_file(cls, f):
        return cls(f.read(cls.struct_size))

    def copy(self):
        return type(self)(self._buffer.tobytes())


WORD = StructField('H', 0)

SHORT = StructField('h', 0)


def short(i):
    i = int(i)
    return (i % 0x8000) - (i & 0x8000)


def byte(i):
    i = int(i)
    return (i % 0x80) - (i & 0x80)


class ObjectMeta(type):
    """the singleton class factory"""

    def __init__(cls, name, bases, clsdict):
        cls._instances = dict()

        def __new__(cls, *args, **kwargs):
            arg_ids = tuple(hash(arg) if hasattr(arg, '__hash__') else id(arg) for arg in args)
            if arg_ids not in cls._instances:
                cls._instances[arg_ids] = Object.__new__(cls)
                cls._instances[arg_ids].__init__(*args, **kwargs)
            return cls._instances[arg_ids]
        clsdict['__new__'] = __new__


singleton = add_metaclass(ObjectMeta)


@singleton
class Object(object):
    """a new-style singleton class base"""


class RunResult(Object):
    success = False


def read_by_struct(struct, bytedata):
    size = struct.struct_size
    return [
        struct(bytedata[i * size:(i + 1) * size])
        for i in range(len(bytedata) // size)
    ]


pal_x = itemgetter(0)
pal_y = itemgetter(1)
pal_h = itemgetter(2)


def pal_xy_offset(pos, x, y):
    vector = pal_x(pos) + x + (pal_y(pos) + y) * 1j
    return int(vector.real), int(vector.imag)


def static_vars(**func_dict):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if not set(wrapped.__dict__) & set(func_dict):
            wrapped.__dict__.update(func_dict)
        return wrapped(*args, **kwargs)
    return wrapper

