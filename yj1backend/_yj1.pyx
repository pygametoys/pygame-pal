from struct import unpack_from
import sys


ctypedef void*               LPVOID
ctypedef const void*         LPCVOID
ctypedef int                 INT


cdef extern from 'yj1.c':
    INT YJ1_Decompress(LPCVOID, LPVOID, INT)
    INT YJ2_Decompress(LPCVOID, LPVOID, INT)


class YJ1Decoder:

    @staticmethod
    def decode(_data):
        data = _data.tobytes()
        cdef const unsigned char *Source = data
        if not len(data):
            return memoryview(b'')
        if data[:4] == b'\x59\x4A\x5F\x31':
            org_len, = unpack_from('I', data, 4)
        else:
            org_len, = unpack_from('I', data)
        if data[:4] == b'\x59\x4A\x5F\x31':
            decompress = YJ1_Decompress
        elif len(data) * 100 < org_len:
            return _data
        else:
            decompress = YJ2_Decompress
        final_data = bytearray(org_len)
        
        cdef char *Dest = final_data
        cdef int orgLen = org_len
        
        dst_len = decompress(Source, Dest, orgLen)
        
        if org_len == dst_len:
            return memoryview(final_data)
        else:
            return _data
