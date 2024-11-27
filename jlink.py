import os
import ctypes
import operator


class JLink(object):
    def __init__(self, dllpath, mcucore):
        self.jlk = ctypes.cdll.LoadLibrary(dllpath)

        self.jlk.JLINKARM_Open()
        if not self.jlk.JLINKARM_IsOpen():
            raise Exception('No JLink connected')

        err_buf = (ctypes.c_char * 64)()
        self.jlk.JLINKARM_ExecCommand(f'Device = {mcucore}'.encode('latin-1'), err_buf, 64)
        
        self.jlk.JLINKARM_TIF_Select(1)
        self.jlk.JLINKARM_SetSpeed(4000)

        self.get_registers()

    def get_registers(self):
        buffer = (ctypes.c_uint32 * 128)()
        n_regs = self.jlk.JLINKARM_GetRegisterList(buffer, 128)

        self.jlk.JLINKARM_GetRegisterName.restype = ctypes.c_char_p

        self.core_regs = {}  # 'name: index' pair
        for index in buffer[:n_regs]:
            name = self.jlk.JLINKARM_GetRegisterName(index).decode()
            self.core_regs[name] = index

        def add_alias(regs, name1, name2, name3):
            if name1 in regs:
                regs[name2] = regs[name1]
                regs[name3] = regs[name1]
            elif name2 in regs:
                regs[name1] = regs[name2]
                regs[name3] = regs[name2]
            elif name3 in regs:
                regs[name1] = regs[name3]
                regs[name2] = regs[name3]
            else:
                raise Exception(f'cannot find {name1}, {name2} or {name3}')

        add_alias(self.core_regs, 'R13', 'SP', 'R13 (SP)')
        add_alias(self.core_regs, 'R14', 'LR', 'R14 (LR)')
        add_alias(self.core_regs, 'R15', 'PC', 'R15 (PC)')

    def write_U8(self, addr, val):
        self.jlk.JLINKARM_WriteU8(addr, val)

    def write_U16(self, addr, val):
        self.jlk.JLINKARM_WriteU16(addr, val)

    def write_U32(self, addr, val):
        self.jlk.JLINKARM_WriteU32(addr, val)

    def write_mem(self, addr, data):
        buffer = (ctypes.c_uint8 * len(data))(*data)

        self.jlk.JLINKARM_WriteMem(addr, len(data), buffer)

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

    def read_U32(self, addr):
        return self.read_mem_U32(addr, 1)[0]

    def read_regs(self, rlist):
        regIndex = [self.core_regs[r] for r in rlist]
        
        regIndex = (ctypes.c_uint32 * len(regIndex))(*regIndex)
        regValue = (ctypes.c_uint32 * len(regIndex))()

        self.jlk.JLINKARM_ReadRegs(regIndex, regValue, 0, len(regIndex))

        return dict(zip(rlist, regValue[:]))

    def write_reg(self, reg, val):
        self.jlk.JLINKARM_WriteReg(self.core_regs[reg.upper()], val)

    def reset(self):
        self.jlk.JLINKARM_Reset()

    def halt(self):
        self.jlk.JLINKARM_Halt()

    def go(self):
        self.jlk.JLINKARM_Go()

    def halted(self):
        ret = self.jlk.JLINKARM_IsHalted()

        return (ret == 1)

    def close(self):
        self.jlk.JLINKARM_Close()


    CORE_TYPE_NAME = {
        0xC20: "Cortex-M0",
        0xC21: "Cortex-M1",
        0xC23: "Cortex-M3",
        0xC24: "Cortex-M4",
        0xC27: "Cortex-M7",
        0xC60: "Cortex-M0+",
        0x132: "STAR"
    }

    def read_core_type(self):
        CPUID = 0xE000ED00
        CPUID_PARTNO_Pos = 4
        CPUID_PARTNO_Msk = 0x0000FFF0
        
        cpuid = self.read_U32(CPUID)

        core_type = (cpuid & CPUID_PARTNO_Msk) >> CPUID_PARTNO_Pos
        
        return self.CORE_TYPE_NAME[core_type]
