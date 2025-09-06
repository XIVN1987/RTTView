import os
import time
import ctypes
import operator


import jlink
import openocd


class XLink(object):
    def __init__(self, xlk):
        self.xlk = xlk

        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.reg_add_alias()

    def open(self, mode, core, speed):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.open(mode, core, speed)

            self.reg_add_alias()
            
        else:
            self.xlk.ap.dp.link.open()

    def reg_add_alias(self):
        def add_alias(regs, name1, name2, name3=None):
            if name1 in regs:
                regs[name2] = regs[name1]
                regs[name3] = regs[name1]
            elif name2 in regs:
                regs[name1] = regs[name2]
                regs[name3] = regs[name2]
            elif name3 and name3 in regs:
                regs[name1] = regs[name3]
                regs[name2] = regs[name3]

        self.xlk.core_regs = {k.lower() : v for k, v in self.xlk.core_regs.items()}

        if self.mode.startswith('arm'):
            add_alias(self.xlk.core_regs, 'r13', 'sp', 'r13 (sp)')
            add_alias(self.xlk.core_regs, 'r14', 'lr', 'r14 (lr)')
            add_alias(self.xlk.core_regs, 'r15', 'pc', 'r15 (pc)')

        elif self.mode.startswith('rv'):
            add_alias(self.xlk.core_regs, 'x1',  'ra')
            add_alias(self.xlk.core_regs, 'x2',  'sp')
            add_alias(self.xlk.core_regs, 'x3',  'gp')
            add_alias(self.xlk.core_regs, 'x4',  'tp')
            add_alias(self.xlk.core_regs, 'x5',  't0')
            add_alias(self.xlk.core_regs, 'x6',  't1')
            add_alias(self.xlk.core_regs, 'x7',  't2')
            add_alias(self.xlk.core_regs, 'x8',  's0', 'fp')
            add_alias(self.xlk.core_regs, 'x9',  's1')
            add_alias(self.xlk.core_regs, 'x10', 'a0')
            add_alias(self.xlk.core_regs, 'x11', 'a1')
            add_alias(self.xlk.core_regs, 'x12', 'a2')
            add_alias(self.xlk.core_regs, 'x13', 'a3')
            add_alias(self.xlk.core_regs, 'x14', 'a4')
            add_alias(self.xlk.core_regs, 'x15', 'a5')
            add_alias(self.xlk.core_regs, 'x16', 'a6')
            add_alias(self.xlk.core_regs, 'x17', 'a7')
            add_alias(self.xlk.core_regs, 'x18', 's2')
            add_alias(self.xlk.core_regs, 'x19', 's3')
            add_alias(self.xlk.core_regs, 'x20', 's4')
            add_alias(self.xlk.core_regs, 'x21', 's5')
            add_alias(self.xlk.core_regs, 'x22', 's6')
            add_alias(self.xlk.core_regs, 'x23', 's7')
            add_alias(self.xlk.core_regs, 'x24', 's8')
            add_alias(self.xlk.core_regs, 'x25', 's9')
            add_alias(self.xlk.core_regs, 'x26', 's10')
            add_alias(self.xlk.core_regs, 'x27', 's11')
            add_alias(self.xlk.core_regs, 'x28', 't3')
            add_alias(self.xlk.core_regs, 'x29', 't4')
            add_alias(self.xlk.core_regs, 'x30', 't5')
            add_alias(self.xlk.core_regs, 'x31', 't6')

    @property
    def mode(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.mode
        else:
            return 'arm'
    
    def write_U8(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U8(addr, val)
        else:
            self.xlk.write8(addr, val)

    def write_U16(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U16(addr, val)
        else:
            self.xlk.write16(addr, val)

    def write_U32(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U32(addr, val)
        else:
            self.xlk.write32(addr, val)

    def write_mem_U8(self, addr, data):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_mem_U8(addr, data)
        else:
            self.xlk.write_memory_block8(addr, data)

    def write_mem_U32(self, addr, data):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_mem_U32(addr, data)
        else:
            self.xlk.write_memory_block32(addr, data)

    def read_mem_U8(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U8(addr, count)
        else:
            return self.xlk.read_memory_block8(addr, count)

    def read_mem_U16(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U16(addr, count)
        else:
            return [self.xlk.read16(addr+i*2) for i in range(count)]

    def read_mem_U32(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U32(addr, count)
        else:
            return self.xlk.read_memory_block32(addr, count)

    def read_U32(self, addr):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_U32(addr)
        else:
            return self.xlk.read32(addr)

    def read_reg(self, reg):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_reg(reg.lower())
        else:
            return self.xlk.read_core_register_raw(reg)

    def read_regs(self, rlist):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return dict(zip(rlist, self.xlk.read_regs([reg.lower() for reg in rlist]).values()))
        else:
            return dict(zip(rlist, self.xlk.read_core_registers_raw(rlist)))

    def write_reg(self, reg, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_reg(reg.lower(), val)
        else:
            self.xlk.write_core_register_raw(reg, val)

    def reset(self):
        self.xlk.reset()

        if self.mode.startswith('rv'):
            self.xlk.write_reg('pc', 0)     # OpenOCD: resume from current code position.
            self.xlk.write_reg('dpc', 0)    # When resuming, PC is updated to value in dpc.
            self.go()
    
    def halt(self):
        self.xlk.halt()

    def step(self):
        self.xlk.step()

    def go(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.go()
        else:
            self.xlk.resume()

    def halted(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.halted()
        else:
            return self.xlk.is_halted()

    def close(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.close()
        else:
            self.xlk.ap.dp.link.close()

    CORE_TYPE_NAME = {
        0xC20: "Cortex-M0",
        0xC21: "Cortex-M1",
        0xC23: "Cortex-M3",
        0xC24: "Cortex-M4",
        0xC27: "Cortex-M7",
        0xC60: "Cortex-M0+",
        0xD20: "Cortex-M23",
        0xD21: "Cortex-M33",
        0xD22: "Cortex-M55",
        0xD23: "Cortex-M85",
        0x132: "Star-MC1"
    }

    def read_core_type(self):
        if self.mode.startswith('arm'):
            CPUID = 0xE000ED00
            CPUID_PARTNO_Pos = 4
            CPUID_PARTNO_Msk = 0x0000FFF0
            
            cpuid = self.read_U32(CPUID)

            core_type = (cpuid & CPUID_PARTNO_Msk) >> CPUID_PARTNO_Pos
            
            return self.CORE_TYPE_NAME[core_type]

        elif self.mode.startswith('rv'):
            halted = self.halted()
            if not halted: self.halt()
            isa = self.read_reg('misa')
            if not halted: self.go()

            if ((isa >> 30) & 3) == 1:
                name = 'RV32'
            elif ((isa >> 62) & 3) == 2:
                name = 'RV64'
            else:
                return 'RISC-V'

            indx = lambda chr: ord(chr) - ord('A')

            if isa & (1 << indx('I')):
                name += 'I'
            else:
                name += 'E'

            if isa & (1 << indx('M')):
                name += 'M'

            if isa & (1 << indx('A')):
                name += 'A'

            if isa & (1 << indx('F')):
                name += 'F'

            if isa & (1 << indx('D')):
                name += 'D'

            if isa & (1 << indx('C')):
                name += 'C'

            if isa & (1 << indx('B')):
                name += 'B'

            name = name.replace('IMAFD', 'G')

            return name

    def reset_and_halt(self):
        if isinstance(self.xlk, openocd.OpenOCD):
            self.xlk.reset(halt=True)

        elif isinstance(self.xlk, jlink.JLink):
            if self.mode.startswith('rv'):
                self.xlk.reset()

            else:   # arm
                self.resetStopOnReset()
                self.write_reg('xpsr', 0x1000000)   # set thumb bit in case the reset handler points to an ARM address

        else:       # daplink only support arm
            self.resetStopOnReset()
            self.write_reg('xpsr', 0x1000000)


    #####################################################################

    # Debug Halting Control and Status Register
    DHCSR = 0xE000EDF0
    C_DEBUGEN   = (1 <<  0)
    C_HALT      = (1 <<  1)
    C_STEP      = (1 <<  2)
    S_REGRDY    = (1 << 16)
    S_HALT      = (1 << 17)
    S_SLEEP     = (1 << 18)
    S_LOCKUP    = (1 << 19)
    S_RETIRE_ST = (1 << 24)     # 1: At least one instruction retired since last DHCSR read.
    S_RESET_ST  = (1 << 25)     # 1: At least one reset since last DHCSR read.

    # Debug Exception and Monitor Control Register
    DEMCR = 0xE000EDFC
    DEMCR_TRCENA       = (1 << 24)
    DEMCR_VC_HARDERR   = (1 << 10)  # Enable halting debug trap on a HardFault exception.
    DEMCR_VC_CORERESET = (1 <<  0)  # Enable Reset Vector Catch. This causes a Local reset to halt a running system.

    def resetStopOnReset(self):
        ''' perform a reset and stop the core on the reset handler '''
        self.halt()

        demcr = self.read_U32(self.DEMCR)

        self.write_U32(self.DEMCR, demcr | self.DEMCR_VC_CORERESET)

        self.reset()
        self.waitReset()
        while not self.halted():
            time.sleep(0.001)

        self.write_U32(self.DEMCR, demcr)

    def waitReset(self):
        ''' wait for the system to come out of reset '''
        startTime = time.time()
        while time.time() - startTime < 2.0:
            try:
                dhcsr = self.read_U32(self.DHCSR)
                if (dhcsr & self.S_RESET_ST) == 0: break
            except Exception as e:
                time.sleep(0.01)
