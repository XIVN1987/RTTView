'''
OpenOCD telnet-protocol python wrapper.
'''
import re
import time
import struct
import telnetlib


class OpenOCD:
    def __init__(self, host="localhost", port=4444, mode='rv', core='risc-v', speed=4000):
        self.host = host
        self.port = port

        self.tnet = telnetlib.Telnet()
        
        self.open(mode, core, speed)

    def open(self, mode='rv', core='risc-v', speed=4000):
        self.mode = mode.lower()

        self.tnet.open(self.host, self.port, 1)
        self._read()

        self.get_registers()

    def _read(self):
        try:
            s = self.tnet.read_until(b'> ', 2).decode('latin-1')
        except:
            return ''
        
        return s[s.find('\n')+1:s.rfind('\n')]
    
    def _exec(self, cmd):
        self.tnet.write(f'{cmd}\n'.encode('latin-1'))
        return self._read()

    def get_registers(self):
        self.core_regs = {}  # 'name: index' pair
        for line in self._exec('reg').splitlines():
            match = re.match(r'\((\d+)\)\s+(\w+)\s+\(/(\d+)\)', line)
            if match:
                self.core_regs[match.group(2)] = match.group(1)

    def halt_required(func):
        def wrapper(self, *args, **kwargs):
            halted = self.halted()
            if not halted: self.halt()
            res = func(self, *args, **kwargs)
            if not halted: self.resume()

            return res

        return wrapper

    @halt_required
    def write_U8(self, addr, val):
        self._exec(f'mwb {addr:#x} {val:#x}')

    @halt_required
    def write_U16(self, addr, val):
        self._exec(f'mwh {addr:#x} {val:#x}')

    @halt_required
    def write_U32(self, addr, val):
        self._exec(f'mww {addr:#x} {val:#x}')

    @halt_required
    def write_U64(self, addr, val):
        self._exec(f'mwd {addr:#x} {val:#x}')

    @halt_required
    def write_mem_(self, addr, data, width):
        index = 0
        while index < len(data):
            s = ' '.join([f'{x:#x}' for x in data[index:index+128]])
            
            self._exec(f'write_memory {addr:#x} {width} {{{s}}}')

            addr += 128 * (width // 8)
            index += 128

    def write_mem_U8(self, addr, data):
        self.write_mem_(addr, data, 8)

    def write_mem_U32(self, addr, data):
        self.write_mem_(addr, data, 32)

    @halt_required
    def read_mem_(self, addr, count, width):
        data = []
        index = 0
        while index < count:    # read too much one-time will cause timeout
            res = self._exec(f'read_memory {addr:#x} {width} {min(128, count)}')
            if res:
                data.extend([int(x, 16) for x in res.split()])

                addr += 128 * (width // 8)
                index += 128

            else:
                break

        return data

    def read_mem_U8(self, addr, count):
        return self.read_mem_(addr, count, 8)

    def read_mem_U16(self, addr, count):
        return self.read_mem_(addr, count, 16)
    
    def read_mem_U32(self, addr, count):
        return self.read_mem_(addr, count, 32)

    def read_mem_U64(self, addr, count):
        return self.read_mem_(addr, count, 64)

    def read_U32(self, addr):
        return self.read_mem_U32(addr, 1)[0]

    def read_U64(self, addr):
        return self.read_mem_U64(addr, 1)[0]

    def read_reg(self, reg):
        res = self._exec(f'reg {self.core_regs[reg]}')

        return int(res.split(':')[1].strip(), 16)

    def read_regs(self, rlist):
        return {reg : self.read_reg(reg) for reg in rlist}

    def write_reg(self, reg, val):
        self._exec(f'reg {self.core_regs[reg]} {val:#x}')

    # halt: immediately halt after reset
    def reset(self, halt=False):
        self._exec(f'reset {"halt" if halt else "run"}')

    def halt(self):
        self._exec('halt 500')

    def step(self, addr=None):
        if addr is None:
            self._exec('step')  # single-step the target at its current code position
        else:
            self._exec(f'step {addr:#x}')   # single-step the target from specified address

    def resume(self, addr=None):
        if addr is None:
            self._exec('resume')    # resume the target at its current code position
        else:
            self._exec(f'resume {addr:#x}') # resume the target to specified address

    def halted(self):
        res = self._exec('poll')

        return 'halted' in res

    def close(self):
        self.tnet.close()

        time.sleep(0.2)



if __name__ == '__main__':
    ocd = OpenOCD()
    ocd.halt()
    res = ocd.read_reg('misa')
    print(f'0x{res:X}')
    res = ocd.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])
    ocd.write_U32(0x20000000, 0x12345678)
    ocd.write_U32(0x20000004, 0x55555555)
    ocd.write_U32(0x20000008, 0xAAAAAAAA)
    ocd.write_U32(0x2000000C, 0x5A5A5A5A)
    res = ocd.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])
    print(ocd.read_regs(['pc', 'ra', 'sp', 'gp']))
    print(ocd.core_regs)
