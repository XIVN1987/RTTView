import os
import ctypes
import operator


import jlink


class XLink(object):
    def __init__(self, xlk):
        self.xlk = xlk

    def open(self, mode, core, speed):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.open(mode, core, speed)
        else:
            self.xlk.ap.dp.link.open()

    def write_U8(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U8(addr, val)
        else:
            self.xlk.write8(addr, val)

    def write_U16(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U16(addr, val)
        else:
            self.xlk.write16(addr, val)

    def write_U32(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U32(addr, val)
        else:
            self.xlk.write32(addr, val)

    def write_mem(self, addr, data):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_mem(addr, data)
        else:
            self.xlk.write_memory_block8(addr, data)

    def read_mem_U8(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U8(addr, count)
        else:
            return [self.xlk.read8(addr+i) for i in range(count)]

    def read_mem_U16(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U16(addr, count)
        else:
            return [self.xlk.read16(addr+i*2) for i in range(count)]

    def read_mem_U32(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U32(addr, count)
        else:
            return [self.xlk.read32(addr+i*4) for i in range(count)]

    def read_U32(self, addr):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_U32(addr)
        else:
            return self.xlk.read32(addr)

    def read_regs(self, rlist):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_regs(rlist)
        else:
            return dict(zip(rlist, self.xlk.read_core_registers_raw(rlist)))

    def read_reg(self, reg):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_reg(reg)
        else:
            return self.xlk.read_core_register_raw(reg)

    def write_reg(self, reg, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_reg(reg, val)
        else:
            self.xlk.write_core_register_raw(reg, val)

    def reset(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.reset()
        else:
            self.xlk.reset()

    def halt(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.halt()
        else:
            self.xlk.halt()

    def go(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.go()
        else:
            self.xlk.resume()

    def halted(self):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.halted()
        else:
            return self.xlk.is_halted()

    def close(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.close()
        else:
            self.xlk.ap.dp.link.close()

    def read_core_type(self):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_core_type()
        else:
            self.xlk._read_core_type()
            if self.xlk.core_type == 0x132:
                return 'STAR-MC1'
            from pyocd.coresight import cortex_m
            return cortex_m.CORE_TYPE_NAME[self.xlk.core_type]
