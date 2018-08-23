# -*- coding: cp936 -*-
# thx to bspal , palxex, palmusicfan and Adam Nielsen
# generated by ctopy
from array import array
import struct
import time
import pyaudio
import pyopl
from pgpal import config
from pgpal.compat import range
from pgpal.mkfext import RIX
from pgpal.sound import adjust_pcm_volume
from threading import Thread

__all__ = ['Rix']


class ADDT:
    def __init__(self):
        self.v = [0x0] * 14


# Playback frequency.  Try a different value if the output sounds stuttery.
freq = config['opl_samplerate']

# How many bytes per sample (2 == 16-bit samples).  This is the only value
# currently implemented.
sample_size = 2

# How many channels to output (2 == stereo).  The OPL2 is mono, so in stereo
# mode the mono samples are copied to both channels.  Enabling OPL3 mode will
# switch the synth to true stereo (and in this case setting num_channels=1
# will just drop the right channel.)  It is done this way so that you can set
# num_channels=2 and output stereo data, and it doesn't matter whether the
# synth is in OPL2 or OPL3 mode - it will always work.
num_channels = 2

# How many samples to synthesise at a time.  Higher values will reduce CPU
# usage but increase lainfo.
synth_size = 512


class OPLStream(object):
    # An OPL helper class which handles the delay between notes and buffering
    def __init__(self, freq, ticks_per_second, stream):
        self.opl = pyopl.opl(
            freq, sampleSize=sample_size, channels=num_channels
        )
        self.ticks_per_second = ticks_per_second
        self.buf = bytearray(synth_size * sample_size * num_channels)
        '''
        pyaudio_buf is a different data type but points to the same memory
        as self.buf, so changing one affects the other.  We put this in the
        constructor so we don't have to recreate it every time we process
        samples, which would eat up CPU time unnecessarily.
        '''
        self.delay = 0
        self.stream = stream

    def write_reg(self, reg, value):
        if config['opl_chip'] == 'opl3':
            self.opl.writeReg(reg + 0x200, value)
        else:
            self.opl.writeReg(reg, value)

    '''
    This is an alternate way of calculating the delay.
    It has slightly higher CPU usage but provides more
    accurate delays (+/- 0.04ms)
    '''
    def wait(self, ticks):
        # Figure out how many samples we need to get to obtain the delay
        fill = ticks * freq // self.ticks_per_second
        tail = fill % synth_size
        if tail:
            buf_tail = bytearray(tail * sample_size * num_channels)
        # Fill the buffer in 512-sample lots until full
        cur = self.buf
        while fill > 1:  # DOSBox synth can't generate < 2 samples
            if fill < synth_size:
                # Resize the buffer for the last bit
                cur = buf_tail
            self.opl.getSamples(cur)
            self.stream.write(adjust_pcm_volume(cur, sample_size))
            fill -= synth_size


class RixInfo(object):
    # global various and flags
    adflag = ([0]*3+[1]*3) * 3
    reg_data = tuple(x for x in range(22) if 1 - x % 8 // 6)
    ad_C0_offs = tuple(i % 3 + (i // 6) * 3 for i in range(18))
    modify = array('I', (
        0,  3,  1,  4,  2,  5,  6,  9, 7, 10, 8, 11, 12, 15,
        13, 16, 14, 17, 12, 15, 16, 0, 14, 0, 17, 0, 13, 0
    ))
    bd_reg_data = array('B',  (
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x08, 0x04, 0x02, 0x01,
        0x00, 0x01, 0x01, 0x03, 0x0F, 0x05, 0x00, 0x01, 0x03, 0x0F, 0x00,
        0x00, 0x00, 0x01, 0x00, 0x00, 0x01, 0x01, 0x0F, 0x07, 0x00, 0x02,
        0x04, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0A,
        0x04, 0x00, 0x08, 0x0C, 0x0B, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00,
        0x00, 0x00, 0x0D, 0x04, 0x00, 0x06, 0x0F, 0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x0C, 0x00, 0x0F, 0x0B, 0x00, 0x08, 0x05, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x0F, 0x0B, 0x00,
        0x07, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,
        0x0F, 0x0B, 0x00, 0x05, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x01, 0x00, 0x0F, 0x0B, 0x00, 0x07, 0x05, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00)
    )
    pause_flag = 0

    def __init__(me):
        me.buf_addr = []
        me.buffer = [0] * 300
        me.mus_block = 0
        me.ins_block = 0
        me.for40reg = [0x7F] * 18
        me.a0b0_data2 = [0] * 11
        me.a0b0_data3 = [0] * 18
        me.a0b0_data4 = [0] * 18
        me.a0b0_data5 = [0] * 96
        me.addrs_head = [0] * 96
        me.rix_stereo = 0
        me.reg_bufs = [ADDT() for _ in range(18)]
        me.mus_time = 0x4268
        me.play_end = 0
        me.music_on = 0
        me.insbuf = [0] * 28
        me.band = 0
        me.band_low = 0
        me.e0_reg_flag = 0
        me.bd_modify = 0
        me.displace = [0] * 11
        me.sustain = 0


def ad_08_reg():
    # prototype of functions
    return ad_bop(8, 0)

def main():
    # MAIN FUNCTION OF THE PROGRAM
    set_new_int()
    data_initial()
    prep_int()

# IMPLENEMTS OF FUNCTIONS                    

def set_new_int():
    ad_initial()

def data_initial():
    info.rix_stereo = info.buf_addr[2]
    info.mus_block = (info.buf_addr[0x0D] << 8)+info.buf_addr[0x0C]
    info.ins_block = (info.buf_addr[0x09] << 8)+info.buf_addr[0x08]
    info.i = info.mus_block+1
    if info.rix_stereo != 0:
        ad_a0b0_reg(6)
        ad_a0b0_reg(7)
        ad_a0b0_reg(8)
        ad_a0b0l_reg(8,0x18, 0)
        ad_a0b0l_reg(7,0x1F, 0)
    info.opl_stream.write_reg(0xa8, 87)
    info.opl_stream.write_reg(0xb8, 9)
    info.opl_stream.write_reg(0xa7, 3)
    info.opl_stream.write_reg(0xb7, 15)
    info.bd_modify = 0
    ad_bd_reg()
    info.band = 0
    info.music_on = 1

def ad_initial():
    for i in range(25):
        res = (i*24+10000)*52088//250000.0*0x24000//0x1B503
        info.buffer[i*12]=(int(res)+4)>>3
        for t in range(12):
            res*=1.06
            info.buffer[i*12+t]=(int(res)+4)>>3
    k = 0
    for i in range(8):
        for j in range(12):
            info.a0b0_data5[k] = i
            info.addrs_head[k] = j
            k += 1
    ad_bd_reg()
    ad_08_reg()
    for i in range(9):
        ad_a0b0_reg(i)
    info.e0_reg_flag = 0x20
    for i in range(18):
        ad_bop(0xE0+info.reg_data[i],0)
    ad_bop(1, info.e0_reg_flag)

def prep_int():
    info.play_end = 0
    while not info.play_end:
        int_08h_entry()

def ad_bop(reg,value):
    info.opl_stream.write_reg(reg & 0xff,value & 0xff)

def int_08h_entry():
    band_sus = 1
    while band_sus:
        if info.sustain <= 0:
            band_sus = rix_proc()
            if band_sus < 0:
                time.sleep(-band_sus)
            elif band_sus:
                info.sustain += band_sus
                info.opl_stream.wait(band_sus)
            else:
                info.play_end = 1
                break
        else:
            if band_sus:
                info.sustain -= 14
            break

def rix_proc():
    ctrl = 0
    if info.music_on == 0:
        return 0
    if info.pause_flag == 1:
        return -0.1
    info.band = 0
    while info.buf_addr[info.i] != 0x80 and info.i<info.filelen-1:
        info.band_low = info.buf_addr[info.i-1]
        ctrl = info.buf_addr[info.i]
        info.i += 2
        if ctrl & 0xF0 == 0x90:    # set instrument
            rix_get_ins()
            rix_90_pro(ctrl & 0x0F)
        elif ctrl & 0xF0 == 0xA0:  # adjust freq  
            rix_A0_pro(ctrl & 0x0F, info.band_low << 6)
        elif ctrl & 0xF0 == 0xB0:  # adjust volume
            rix_B0_pro(ctrl & 0x0F, info.band_low)
        elif ctrl & 0xF0 == 0xC0:  # set music note
            switch_ad_bd(ctrl & 0x0F)
            if info.band_low != 0: 
                rix_C0_pro(ctrl & 0x0F, info.band_low-1)
        else:
            info.band = (ctrl << 8)+info.band_low
        if info.band != 0:
            return info.band
    music_ctrl()
    info.i = info.mus_block+1
    info.band = 0
    info.music_on = 1
    return 0

def rix_get_ins():
    pos = info.ins_block+(info.band_low << 6)
    for i in range(0, 56, 2):
        info.insbuf[i//2] = (info.buf_addr[pos+i+1] << 8) + info.buf_addr[pos+i]

def rix_90_pro(ctrl_l):
    if info.rix_stereo == 0 or ctrl_l < 6:
        ins_to_reg(info.modify[ctrl_l*2],info.insbuf,info.insbuf[26])
        ins_to_reg(info.modify[ctrl_l*2+1],info.insbuf[13:],info.insbuf[27])
    else:
        if ctrl_l > 6:
            ins_to_reg(info.modify[ctrl_l*2+6],info.insbuf,info.insbuf[26])
        else:
            ins_to_reg(12,info.insbuf,info.insbuf[26])
            ins_to_reg(15,info.insbuf[13:],info.insbuf[27])

def rix_A0_pro(ctrl_l, index):
    if info.rix_stereo == 0 or ctrl_l <= 6:
        prepare_a0b0(ctrl_l,0x3FFF if index>0x3FFF else index)
        ad_a0b0l_reg(ctrl_l,info.a0b0_data3[ctrl_l],info.a0b0_data4[ctrl_l])

def prepare_a0b0(index, v):  # important !
    high = low = 0
    res = (v-0x2000)*0x19
    if res == 0xFF and v>=0x2000: return
    res = (high|low)//0x2000
    low = res&0xFFFF
    if low < 0:
        low = 0x18-low
        high = 0xFFFF if low<0 else 0
        res = high
        res<<=16
        res+=low
        low = res//0xFFE7
        info.a0b0_data2[index] = low
        low = res
        res = low - 0x18
        high = res%0x19
        low = res//0x19
        if high != 0:
            low = 0x19
            low = low-high
    else:
        res = high = low
        low = res//0x19
        info.a0b0_data2[index] = low
        res = high
        low = res % 0x19
    low *= 0x18
    info.displace[index] = low

def ad_a0b0l_reg(index, p2, p3):
    i = p2+info.a0b0_data2[index]
    info.a0b0_data4[index] = p3
    info.a0b0_data3[index] = p2
    i = i if i<=0x5F else 0x5F
    i = i if i>=0 else 0
    data = info.buffer[info.addrs_head[i]+info.displace[index]//2]
    ad_bop(0xA0+index, data)
    data = info.a0b0_data5[i]*4+(0 if p3<1 else 0x20)+((data>>8)&3)
    ad_bop(0xB0+index, data)

def rix_B0_pro(ctrl_l, index):
    temp = 0
    if info.rix_stereo == 0 or ctrl_l < 6: temp = info.modify[ctrl_l*2+1]
    else:
        temp = ctrl_l*2 if ctrl_l > 6 else ctrl_l*2+1
        temp = info.modify[temp+6]
    info.for40reg[temp] = 0x7F if index>0x7F else index
    ad_40_reg(temp)

def rix_C0_pro(ctrl_l, index):
    i = index-12 if index>=12 else 0
    if ctrl_l < 6 or info.rix_stereo == 0:
        ad_a0b0l_reg(ctrl_l,i,1)
    else:
        if ctrl_l != 6:
            if ctrl_l == 8:
                ad_a0b0l_reg(ctrl_l,i,0)
                ad_a0b0l_reg(7,i+7,0)
        else: 
            ad_a0b0l_reg(ctrl_l,i,0)
        info.bd_modify |= info.bd_reg_data[ctrl_l]
        ad_bd_reg()

def switch_ad_bd(index):
    if info.rix_stereo == 0 or index < 6: 
        ad_a0b0l_reg(index,info.a0b0_data3[index],0)
    else:
        info.bd_modify &= (~info.bd_reg_data[index])
        ad_bd_reg()

def ins_to_reg(index, insb, value):
    info.reg_bufs[index].v[:13] = insb[:13]
    info.reg_bufs[index].v[13] = value&3
    ad_bd_reg()
    ad_08_reg()
    ad_40_reg(index)
    ad_C0_reg(index)
    ad_60_reg(index)
    ad_80_reg(index)
    ad_20_reg(index)
    ad_E0_reg(index)

def ad_E0_reg(index):
    data = 0 if info.e0_reg_flag == 0 else (info.reg_bufs[index].v[13]&3)
    ad_bop(0xE0+info.reg_data[index], data)

def ad_20_reg(index):
    data = 0 if info.reg_bufs[index].v[9] < 1 else 0x80
    data +=0 if info.reg_bufs[index].v[10] < 1 else 0x40
    data +=0 if info.reg_bufs[index].v[5] < 1 else 0x20
    data +=0 if info.reg_bufs[index].v[11] < 1 else 0x10
    data += (info.reg_bufs[index].v[1]&0x0F)
    ad_bop(0x20+info.reg_data[index], data)

def ad_80_reg(index):
    data = info.reg_bufs[index].v[7]&0x0F
    temp = info.reg_bufs[index].v[4]
    data |= (temp << 4)
    ad_bop(0x80+info.reg_data[index], data)

def ad_60_reg(index):
    data = info.reg_bufs[index].v[6]&0x0F
    temp = info.reg_bufs[index].v[3]
    data |= (temp << 4)
    ad_bop(0x60+info.reg_data[index], data)

def ad_C0_reg(index):
    data = info.reg_bufs[index].v[2]
    if info.adflag[index] == 1: return
    data *= 2
    data |= 1 if info.reg_bufs[index].v[12] < 1 else 0
    ad_bop(0xC0+info.ad_C0_offs[index], data)

def ad_40_reg(index):
    res = 0
    data = 0
    temp = info.reg_bufs[index].v[0]
    data = 0x3F - (0x3F & info.reg_bufs[index].v[8])
    data *= info.for40reg[index]
    data *= 2
    data += 0x7F
    res = data
    data = res//0xFE
    data -= 0x3F
    data = -data
    data |= temp<<6
    ad_bop(0x40+info.reg_data[index], data)

def ad_bd_reg():
    data = 0 if info.rix_stereo < 1 else 0x20
    data |= info.bd_modify
    ad_bop(0xBD, data)

def ad_a0b0_reg(index):
    ad_bop(0xA0+index, 0)
    ad_bop(0xB0+index, 0)

def music_ctrl():
    info.music_on = 0
    for i in range(11):
        switch_ad_bd(i)

info = RixInfo()

def rixdup(rix_data):
    """
    taken from palresearch rix utils
    """
    if len(rix_data) < 0xC:
        return rix_data
    rhythm_offset, = struct.unpack_from("<I", rix_data, 0xC)
    new_data = rix_data[:rhythm_offset]
    for _ in range(2):  # dup whole rhythms 2 times!
        new_data += rix_data[rhythm_offset: -2]
    for _ in range(11):  # mute all channels
        new_data += struct.pack("<BB", 0, 0xC0 + _)
    for _ in range(1):  # delay time
        new_data += struct.pack("<BB", 0, 1)
    new_data += rix_data[-2:]
    return new_data


class RixPlayer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.i = ''
        self.ended = False
        self.loop = -1
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.audio.get_format_from_width(sample_size),
            channels=num_channels,
            rate=freq,
            output=True,
            frames_per_buffer=1024
        )

    def prepare(self):
        ticks_per_second = 1000
        # Set up the OPL synth
        info.opl_stream = OPLStream(freq, ticks_per_second, self.stream)
        # Enable Wavesel on OPL2
        info.opl_stream.write_reg(1, 32)
        if config['opl_chip'] == 'opl3':
            info.opl_stream.write_reg(0x105, 1)
        self.stream.start_stream()

    def run(self):
        # Set up the audio stream

        # At this point we have to hope PyAudio has got us the audio format we
        # requested.  It doesn't always, but it lacks functions for us to check
        # This means we could end up outputting data in the wrong format...
        while not self.ended:
            self.prepare()
            try:
                self.play()
            except IOError:
                if self.ended:
                    break
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

    def play(self):
        if len(self.i) and not self.ended:
            info.buf_addr = bytearray(rixdup(self.i))
            info.filelen = len(self.i)
            if self.loop == 0:
                self.i = ''
            main()
            info.__init__()
        else:
            time.sleep(0.1)

    def stop(self):
        self.i = ''
        music_ctrl()
        info.__init__()


class Rix(object):

    def __init__(self):
        self.player = RixPlayer()
        self.player.start()
        self.file = RIX()

    def load(self, index):
        self.data = self.file.read(index, True)
        return True

    def play(self, loop):
        self.player.stop()
        self.player.loop = loop
        self.player.i = self.data

    def pause(self):
        info.pause_flag = 1

    def unpause(self):
        info.pause_flag = 0

    def stop(self):
        self.player.stop()

    def quit(self):
        self.player.ended = True
        self.stop()
        self.player.join()
