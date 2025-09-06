import ctypes


class JLink(object):
    def __init__(self, dllpath, mode='arm', core='Cortex-M0', speed=4000):
        self.jlk = ctypes.cdll.LoadLibrary(dllpath)

        self.open(mode, core, speed)

    def open(self, mode='arm', core='Cortex-M0', speed=4000):
        self.mode = mode.lower()

        self.jlk.JLINKARM_Open()
        if not self.jlk.JLINKARM_IsOpen():
            raise Exception('No JLink connected')

        err_buf = (ctypes.c_char * 64)()
        self.jlk.JLINKARM_ExecCommand(f'Device = {core}'.encode('latin-1'), err_buf, 64)
        
        if self.mode == 'arm':
            tif = TIF.SWD
        elif self.mode == 'rv':
            tif = TIF.CJTAG
        elif self.mode in ('armj', 'rvj'):
            tif = TIF.JTAG
        else:
            raise Exception('invalid mode value')

        self.jlk.JLINKARM_TIF_Select(tif)
        self.jlk.JLINKARM_SetSpeed(speed)

        self.get_registers()

    def get_registers(self):
        buffer = (ctypes.c_uint32 * 0x4000)()
        n_regs = self.jlk.JLINKARM_GetRegisterList(buffer, 0x4000)

        self.jlk.JLINKARM_GetRegisterName.restype = ctypes.c_char_p

        self.core_regs = {}  # 'name: index' pair
        for index in buffer[:n_regs]:
            name = self.jlk.JLINKARM_GetRegisterName(index).decode()
            self.core_regs[name] = index

    def write_U8(self, addr, val):
        self.jlk.JLINKARM_WriteU8(addr, val)

    def write_U16(self, addr, val):
        self.jlk.JLINKARM_WriteU16(addr, val)

    def write_U32(self, addr, val):
        self.jlk.JLINKARM_WriteU32(addr, val)

    def write_U64(self, addr, val):
        self.jlk.JLINKARM_WriteU64(addr, val)

    def write_mem_U8(self, addr, data):
        buffer = (ctypes.c_uint8 * len(data))(*data)

        self.jlk.JLINKARM_WriteMem(addr, len(data), buffer)

    def write_mem_U32(self, addr, data):
        buffer = (ctypes.c_uint32 * len(data))(*data)

        self.write_mem_U8(addr, bytes(buffer))  # MCU and PC both little-endian

    def read_mem_U8(self, addr, count):
        buffer = (ctypes.c_uint8 * count)()
        self.jlk.JLINKARM_ReadMemU8(addr, count, buffer, 0)

        return buffer[:]

    def read_mem_U16(self, addr, count):
        buffer = (ctypes.c_uint16 * count)()
        self.jlk.JLINKARM_ReadMemU16(addr, count, buffer, 0)

        return buffer[:]

    def read_mem_U32(self, addr, count):
        buffer = (ctypes.c_uint32 * count)()
        self.jlk.JLINKARM_ReadMemU32(addr, count, buffer, 0)

        return buffer[:]

    def read_mem_U64(self, addr, count):
        buffer = (ctypes.c_uint64 * count)()
        self.jlk.JLINKARM_ReadMemU64(addr, count, buffer, 0)

        return buffer[:]

    def read_U32(self, addr):
        return self.read_mem_U32(addr, 1)[0]

    def read_U64(self, addr):
        return self.read_mem_U64(addr, 1)[0]

    def read_reg(self, reg):
        val = self.jlk.JLINKARM_ReadReg(self.core_regs[reg])
        if val < 0:
            val += 1 << 32

        return val
    
    def read_regs(self, rlist):
        regIndex = [self.core_regs[reg] for reg in rlist]
        
        regIndex = (ctypes.c_uint32 * len(regIndex))(*regIndex)
        regValue = (ctypes.c_uint32 * len(regIndex))()

        self.jlk.JLINKARM_ReadRegs(regIndex, regValue, 0, len(regIndex))

        return dict(zip(rlist, regValue[:]))

    def write_reg(self, reg, val):
        self.jlk.JLINKARM_WriteReg(self.core_regs[reg], val)

    def reset(self):
        self.jlk.JLINKARM_Reset()

    def halt(self):
        self.jlk.JLINKARM_Halt()

    def step(self):
        self.jlk.JLINKARM_Step()

    def go(self):
        self.jlk.JLINKARM_Go()

    def halted(self):
        return self.jlk.JLINKARM_IsHalted()

    def close(self):
        self.jlk.JLINKARM_Close()


class TIF:
    JTAG  = 0
    SWD   = 1
    CJTAG = 7



if __name__ == '__main__':
    jlk = JLink(r'D:\Program\Segger\JLink_V688\JLink_x64.dll')
    jlk.halt()
    res = jlk.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])
    jlk.write_U32(0x20000000, 0x12345678)
    jlk.write_U32(0x20000004, 0x55555555)
    jlk.write_U32(0x20000008, 0xAAAAAAAA)
    jlk.write_U32(0x2000000C, 0x5A5A5A5A)
    res = jlk.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])
    print(jlk.read_regs(['R15 (PC)', 'R14', 'R13 (SP)']))
    print(jlk.core_regs)
