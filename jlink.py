import os
import ctypes
import operator


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

        if self.mode.startswith('arm'):
            add_alias(self.core_regs, 'R13', 'SP', 'R13 (SP)')
            add_alias(self.core_regs, 'R14', 'LR', 'R14 (LR)')
            add_alias(self.core_regs, 'R15', 'PC', 'R15 (PC)')

        elif self.mode.startswith('rv'):
            add_alias(self.core_regs, 'X1',  'RA',  '')
            add_alias(self.core_regs, 'X2',  'SP',  '')
            add_alias(self.core_regs, 'X3',  'GP',  '')
            add_alias(self.core_regs, 'X4',  'TP',  '')
            add_alias(self.core_regs, 'X5',  'T0',  '')
            add_alias(self.core_regs, 'X6',  'T1',  '')
            add_alias(self.core_regs, 'X7',  'T2',  '')
            add_alias(self.core_regs, 'X8',  'S0',  'FP')
            add_alias(self.core_regs, 'X9',  'S1',  '')
            add_alias(self.core_regs, 'X10', 'A0',  '')
            add_alias(self.core_regs, 'X11', 'A1',  '')
            add_alias(self.core_regs, 'X12', 'A2',  '')
            add_alias(self.core_regs, 'X13', 'A3',  '')
            add_alias(self.core_regs, 'X14', 'A4',  '')
            add_alias(self.core_regs, 'X15', 'A5',  '')
            add_alias(self.core_regs, 'X16', 'A6',  '')
            add_alias(self.core_regs, 'X17', 'A7',  '')
            add_alias(self.core_regs, 'X18', 'S2',  '')
            add_alias(self.core_regs, 'X19', 'S3',  '')
            add_alias(self.core_regs, 'X20', 'S4',  '')
            add_alias(self.core_regs, 'X21', 'S5',  '')
            add_alias(self.core_regs, 'X22', 'S6',  '')
            add_alias(self.core_regs, 'X23', 'S7',  '')
            add_alias(self.core_regs, 'X24', 'S8',  '')
            add_alias(self.core_regs, 'X25', 'S9',  '')
            add_alias(self.core_regs, 'X26', 'S10', '')
            add_alias(self.core_regs, 'X27', 'S11', '')
            add_alias(self.core_regs, 'X28', 'T3',  '')
            add_alias(self.core_regs, 'X29', 'T4',  '')
            add_alias(self.core_regs, 'X30', 'T5',  '')
            add_alias(self.core_regs, 'X31', 'T6',  '')

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

    def read_reg(self, reg):
        return self.jlk.JLINKARM_ReadReg(self.core_regs[reg.upper()])
    
    def read_regs(self, rlist):
        regIndex = [self.core_regs[reg.upper()] for reg in rlist]
        
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
        return self.jlk.JLINKARM_IsHalted()

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
            isa = self.read_reg('MISA')
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


class TIF:
    JTAG  = 0
    SWD   = 1
    CJTAG = 7


class CM4_REG:
    R0              =  0
    R1              =  1
    R2              =  2
    R3              =  3
    R4              =  4
    R5              =  5
    R6              =  6
    R7              =  7
    R8              =  8
    R9              =  9
    R10             = 10
    R11             = 11
    R12             = 12
    R13             = 13  # Pseudo reg! It needs to be mapped to SP_MSP or SP_PSP, depending on current Controlregister:
    R14             = 14
    R15             = 15
    XPSR            = 16
    MSP             = 17
    PSP             = 18
    RAZ             = 19  # Reserved
    CFBP            = 20  # CONTROL/FAULTMASK/BASEPRI/PRIMASK (packed into 4 bytes of word. CONTROL = CFBP[31:24], FAULTMASK = CFBP[16:23], BASEPRI = CFBP[15:8], PRIMASK = CFBP[7:0]
    APSR            = 21  # Pseudo reg. (Part of XPSR)
    EPSR            = 22  # Pseudo reg. (Part of XPSR)
    IPSR            = 23  # Pseudo reg. (Part of XPSR)
    PRIMASK         = 24  # Pseudo reg. (Part of CFBP)
    BASEPRI         = 25  # Pseudo reg. (Part of CFBP)
    FAULTMASK       = 26  # Pseudo reg. (Part of CFBP)
    CONTROL         = 27  # Pseudo reg. (Part of CFBP)
    BASEPRI_MAX     = 28  # Pseudo reg. (Part of CFBP)
    IAPSR           = 29  # Pseudo reg. (Part of XPSR)
    EAPSR           = 30  # Pseudo reg. (Part of XPSR)
    IEPSR           = 31  # Pseudo reg. (Part of XPSR)
    FPSCR           = 32
    FPS0            = 33
    FPS1            = 34
    FPS2            = 35
    FPS3            = 36
    FPS4            = 37
    FPS5            = 38
    FPS6            = 39
    FPS7            = 40
    FPS8            = 41
    FPS9            = 42
    FPS10           = 43
    FPS11           = 44
    FPS12           = 45
    FPS13           = 46
    FPS14           = 47
    FPS15           = 48
    FPS16           = 49
    FPS17           = 50
    FPS18           = 51
    FPS19           = 52
    FPS20           = 53
    FPS21           = 54
    FPS22           = 55
    FPS23           = 56
    FPS24           = 57
    FPS25           = 58
    FPS26           = 59
    FPS27           = 60
    FPS28           = 61
    FPS29           = 62
    FPS30           = 63
    FPS31           = 64
    DWT_CYCCNT      = 65
    #
    # New regs introduced with ARMv8M architecture
    #
    MSP_NS          = 66
    PSP_NS          = 67
    MSP_S           = 68
    PSP_S           = 69
    MSPLIM_S        = 70
    PSPLIM_S        = 71
    MSPLIM_NS       = 72
    PSPLIM_NS       = 73
    CFBP_S          = 74
    CFBP_NS         = 75
    PRIMASK_NS      = 75  # Pseudo reg. (Part of CFBP)
    BASEPRI_NS      = 76  # Pseudo reg. (Part of CFBP)
    FAULTMASK_NS    = 77  # Pseudo reg. (Part of CFBP)
    CONTROL_NS      = 78  # Pseudo reg. (Part of CFBP)
    BASEPRI_MAX_NS  = 79  # Pseudo reg. (Part of CFBP)
    PRIMASK_S       = 80  # Pseudo reg. (Part of CFBP)
    BASEPRI_S       = 81  # Pseudo reg. (Part of CFBP)
    FAULTMASK_S     = 82  # Pseudo reg. (Part of CFBP)
    CONTROL_S       = 83  # Pseudo reg. (Part of CFBP)
    BASEPRI_MAX_S   = 84  # Pseudo reg. (Part of CFBP)
    MSPLIM          = 85  # Either real or pseudo reg, depending on if security extensions are implemented or not
    PSPLIM          = 86  # Either real or pseudo reg, depending on if security extensions are implemented or not


class RISCV_REG:
    FFLAGS          = 0x001  # Bits [4:0] of FCSR
    FRM             = 0x002  # Bits [7:5] of FCSR
    FCSR            = 0x003  # Always 32-bit
    
    USTATUS         = 0x000  # 32/64-bit. Depends on RV32/64
    UIE             = 0x004  # 32/64-bit. Depends on RV32/64
    UTVEC           = 0x005  # Length = ???
    USCRATCH        = 0x040  # Length = ???
    UEPC            = 0x041  # 32/64-bit. Depends on RV32/64
    UCAUSE          = 0x042  # Length = ???
    UTVAL           = 0x043  # Length = ???
    UIP             = 0x044  # 32/64-bit. Depends on RV32/64
    
    SSTATUS         = 0x100  # 32/64-bit. Depends on RV32/64
    SEDELEG         = 0x102  # 32/64-bit. Depends on RV32/64
    SIDELEG         = 0x103  # 32/64-bit. Depends on RV32/64
    SIE             = 0x104  # 32/64-bit. Depends on RV32/64
    STVEC           = 0x105  # 32/64-bit. Depends on RV32/64
    SCOUNTEREN      = 0x106  # Always 32-bit
    SSCRATCH        = 0x140  # 32/64-bit. Depends on RV32/64
    SEPC            = 0x141  # 32/64-bit. Depends on RV32/64
    SCAUSE          = 0x142  # 32/64-bit. Depends on RV32/64
    STVAL           = 0x143  # 32/64-bit. Depends on RV32/64
    SIP             = 0x144  # 32/64-bit. Depends on RV32/64
    SATP            = 0x180  # 32/64-bit. Depends on RV32/64
    
    MSTATUS         = 0x300  # 32/64-bit. Depends on RV32/64
    MISA            = 0x301  # 32/64-bit. Depends on RV32/64
    MEDELEG         = 0x302  # 32/64-bit. Depends on RV32/64
    MIDELEG         = 0x303  # 32/64-bit. Depends on RV32/64
    MIE             = 0x304  # 32/64-bit. Depends on RV32/64
    MTVEC           = 0x305  # 32/64-bit. Depends on RV32/64
    MCOUNTEREN      = 0x306  # Always 32-bit
    MHPMEVENT3      = 0x323  # 32/64-bit. Depends on RV32/64
    MHPMEVENT4      = 0x324  # 32/64-bit. Depends on RV32/64
    MHPMEVENT5      = 0x325  # 32/64-bit. Depends on RV32/64
    MHPMEVENT6      = 0x326  # 32/64-bit. Depends on RV32/64
    MHPMEVENT7      = 0x327  # 32/64-bit. Depends on RV32/64
    MHPMEVENT8      = 0x328  # 32/64-bit. Depends on RV32/64
    MHPMEVENT9      = 0x329  # 32/64-bit. Depends on RV32/64
    MHPMEVENT10     = 0x32A  # 32/64-bit. Depends on RV32/64
    MHPMEVENT11     = 0x32B  # 32/64-bit. Depends on RV32/64
    MHPMEVENT12     = 0x32C  # 32/64-bit. Depends on RV32/64
    MHPMEVENT13     = 0x32D  # 32/64-bit. Depends on RV32/64
    MHPMEVENT14     = 0x32E  # 32/64-bit. Depends on RV32/64
    MHPMEVENT15     = 0x32F  # 32/64-bit. Depends on RV32/64
    MHPMEVENT16     = 0x330  # 32/64-bit. Depends on RV32/64
    MHPMEVENT17     = 0x331  # 32/64-bit. Depends on RV32/64
    MHPMEVENT18     = 0x332  # 32/64-bit. Depends on RV32/64
    MHPMEVENT19     = 0x333  # 32/64-bit. Depends on RV32/64
    MHPMEVENT20     = 0x334  # 32/64-bit. Depends on RV32/64
    MHPMEVENT21     = 0x335  # 32/64-bit. Depends on RV32/64
    MHPMEVENT22     = 0x336  # 32/64-bit. Depends on RV32/64
    MHPMEVENT23     = 0x337  # 32/64-bit. Depends on RV32/64
    MHPMEVENT24     = 0x338  # 32/64-bit. Depends on RV32/64
    MHPMEVENT25     = 0x339  # 32/64-bit. Depends on RV32/64
    MHPMEVENT26     = 0x33A  # 32/64-bit. Depends on RV32/64
    MHPMEVENT27     = 0x33B  # 32/64-bit. Depends on RV32/64
    MHPMEVENT28     = 0x33C  # 32/64-bit. Depends on RV32/64
    MHPMEVENT29     = 0x33D  # 32/64-bit. Depends on RV32/64
    MHPMEVENT30     = 0x33E  # 32/64-bit. Depends on RV32/64
    MHPMEVENT31     = 0x33F  # 32/64-bit. Depends on RV32/64
    MSCRATCH        = 0x340  # 32/64-bit. Depends on RV32/64
    MEPC            = 0x341  # 32/64-bit. Depends on RV32/64
    MCAUSE          = 0x342  # 32/64-bit. Depends on RV32/64
    MTVAL           = 0x343  # 32/64-bit. Depends on RV32/64
    MIP             = 0x344  # 32/64-bit. Depends on RV32/64
    
    PMPCFG0         = 0x3A0  # Always 32-bit
    PMPCFG1         = 0x3A1  # Always 32-bit
    PMPCFG2         = 0x3A2  # Always 32-bit
    PMPCFG3         = 0x3A3  # Always 32-bit
    PMPADDR0        = 0x3B0  # 32/64-bit. Depends on RV32/64
    PMPADDR1        = 0x3B1  # 32/64-bit. Depends on RV32/64
    PMPADDR2        = 0x3B2  # 32/64-bit. Depends on RV32/64
    PMPADDR3        = 0x3B3  # 32/64-bit. Depends on RV32/64
    PMPADDR4        = 0x3B4  # 32/64-bit. Depends on RV32/64
    PMPADDR5        = 0x3B5  # 32/64-bit. Depends on RV32/64
    PMPADDR6        = 0x3B6  # 32/64-bit. Depends on RV32/64
    PMPADDR7        = 0x3B7  # 32/64-bit. Depends on RV32/64
    PMPADDR8        = 0x3B8  # 32/64-bit. Depends on RV32/64
    PMPADDR9        = 0x3B9  # 32/64-bit. Depends on RV32/64
    PMPADDR10       = 0x3BA  # 32/64-bit. Depends on RV32/64
    PMPADDR11       = 0x3BB  # 32/64-bit. Depends on RV32/64
    PMPADDR12       = 0x3BC  # 32/64-bit. Depends on RV32/64
    PMPADDR13       = 0x3BD  # 32/64-bit. Depends on RV32/64
    PMPADDR14       = 0x3BE  # 32/64-bit. Depends on RV32/64
    PMPADDR15       = 0x3BF  # 32/64-bit. Depends on RV32/64
    
    TSELECT         = 0x7A0  # 32/64-bit. Depends on RV32/64
    TDATA1          = 0x7A1  # 32/64-bit. Depends on RV32/64
    TDATA2          = 0x7A2  # 32/64-bit. Depends on RV32/64
    TDATA3          = 0x7A3  # 32/64-bit. Depends on RV32/64
    DCSR            = 0x7B0  # Always 32-bit
    DPC             = 0x7B1  # 32/64-bit. Depends on RV32/64
    DSCRATCH        = 0x7B2  # ???
    
    MCYCLE          = 0xB00  # Always 64bit. For RV32, higher bits can be accessed via MCYCLEH
    MINSTRET        = 0xB02  # Always 64bit. For RV32, higher bits can be accessed via MINSTRETH
    MHPMCOUNTER3    = 0xB03  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER4    = 0xB04  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER5    = 0xB05  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER6    = 0xB06  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER7    = 0xB07  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER8    = 0xB08  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER9    = 0xB09  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER10   = 0xB0A  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER11   = 0xB0B  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER12   = 0xB0C  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER13   = 0xB0D  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER14   = 0xB0E  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER15   = 0xB0F  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER16   = 0xB10  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER17   = 0xB11  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER18   = 0xB12  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER19   = 0xB13  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER20   = 0xB14  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER21   = 0xB15  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER22   = 0xB16  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER23   = 0xB17  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER24   = 0xB18  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER25   = 0xB19  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER26   = 0xB1A  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER27   = 0xB1B  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER28   = 0xB1C  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER29   = 0xB1D  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER30   = 0xB1E  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    MHPMCOUNTER31   = 0xB1F  # Always 64bit. For RV32, higher bits can be accessed via MHPMCOUNTERxH
    
    MCYCLEH         = 0xB80  # Higher 32-bits of MCYCLE (needed for RV32)
    MINSTRETH       = 0xB82  # Higher 32-bits of MINSTRET (needed for RV32)
    MHPMCOUNTER3H   = 0xB83  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER4H   = 0xB84  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER5H   = 0xB85  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER6H   = 0xB86  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER7H   = 0xB87  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER8H   = 0xB88  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER9H   = 0xB89  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER10H  = 0xB8A  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER11H  = 0xB8B  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER12H  = 0xB8C  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER13H  = 0xB8D  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER14H  = 0xB8E  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER15H  = 0xB8F  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER16H  = 0xB90  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER17H  = 0xB91  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER18H  = 0xB92  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER19H  = 0xB93  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER20H  = 0xB94  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER21H  = 0xB95  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER22H  = 0xB96  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER23H  = 0xB97  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER24H  = 0xB98  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER25H  = 0xB99  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER26H  = 0xB9A  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER27H  = 0xB9B  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER28H  = 0xB9C  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER29H  = 0xB9D  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER30H  = 0xB9E  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    MHPMCOUNTER31H  = 0xB9F  # Higher 32-bits of MHPMCOUNTERx (needed for RV32)
    
    CYCLE           = 0xC00  # Always 64-bit. For RV32, higher bits can be accessed via CYCLEH
    TIME            = 0xC01  # Always 64-bit. For RV32, higher bits can be accessed via TIMEH
    INSTRET         = 0xC02  # Always 64-bit. For RV32, higher bits can be accessed via INSTRETH
    HPMCOUNTER3     = 0xC03  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER4     = 0xC04  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER5     = 0xC05  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER6     = 0xC06  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER7     = 0xC07  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER8     = 0xC08  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER9     = 0xC09  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER10    = 0xC0A  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER11    = 0xC0B  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER12    = 0xC0C  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER13    = 0xC0D  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER14    = 0xC0E  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER15    = 0xC0F  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER16    = 0xC10  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER17    = 0xC11  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER18    = 0xC12  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER19    = 0xC13  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER20    = 0xC14  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER21    = 0xC15  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER22    = 0xC16  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER23    = 0xC17  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER24    = 0xC18  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER25    = 0xC19  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER26    = 0xC1A  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER27    = 0xC1B  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER28    = 0xC1C  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER29    = 0xC1D  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER30    = 0xC1E  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    HPMCOUNTER31    = 0xC1F  # Always 64bit. For RV32, higher bits can be accessed via HPMCOUNTERxH
    
    CYCLEH          = 0xC80  # Higher 32-bit of CYCLE (needed for RV32)
    TIMEH           = 0xC81  # Higher 32-bit of TIME (needed for RV32)
    INSTRETH        = 0xC82  # Higher 32-bit of INSTRET (needed for RV32)
    HPMCOUNTER3H    = 0xC83  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER4H    = 0xC84  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER5H    = 0xC85  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER6H    = 0xC86  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER7H    = 0xC87  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER8H    = 0xC88  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER9H    = 0xC89  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER10H   = 0xC8A  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER11H   = 0xC8B  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER12H   = 0xC8C  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER13H   = 0xC8D  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER14H   = 0xC8E  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER15H   = 0xC8F  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER16H   = 0xC90  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER17H   = 0xC91  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER18H   = 0xC92  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER19H   = 0xC93  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER20H   = 0xC94  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER21H   = 0xC95  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER22H   = 0xC96  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER23H   = 0xC97  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER24H   = 0xC98  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER25H   = 0xC99  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER26H   = 0xC9A  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER27H   = 0xC9B  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER28H   = 0xC9C  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER29H   = 0xC9D  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER30H   = 0xC9E  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    HPMCOUNTER31H   = 0xC9F  # Higher 32-bits of HPMCOUNTERx (Needed for RV32)
    
    MVENDORID       = 0xF11  # 32/64-bit. Depends on RV32/64
    MARCHID         = 0xF12  # 32/64-bit. Depends on RV32/64
    MIMPID          = 0xF13  # 32/64-bit. Depends on RV32/64
    MHARTID         = 0xF14  # 32/64-bit. Depends on RV32/64
    
    X0              = 0x1000 # 32/64-bit. Depends on RV32/64
    X1              = 0x1001 # 32/64-bit. Depends on RV32/64
    X2              = 0x1002 # 32/64-bit. Depends on RV32/64
    X3              = 0x1003 # 32/64-bit. Depends on RV32/64
    X4              = 0x1004 # 32/64-bit. Depends on RV32/64
    X5              = 0x1005 # 32/64-bit. Depends on RV32/64
    X6              = 0x1006 # 32/64-bit. Depends on RV32/64
    X7              = 0x1007 # 32/64-bit. Depends on RV32/64
    X8              = 0x1008 # 32/64-bit. Depends on RV32/64
    X9              = 0x1009 # 32/64-bit. Depends on RV32/64
    X10             = 0x100A # 32/64-bit. Depends on RV32/64
    X11             = 0x100B # 32/64-bit. Depends on RV32/64
    X12             = 0x100C # 32/64-bit. Depends on RV32/64
    X13             = 0x100D # 32/64-bit. Depends on RV32/64
    X14             = 0x100E # 32/64-bit. Depends on RV32/64
    X15             = 0x100F # 32/64-bit. Depends on RV32/64
    X16             = 0x1010 # 32/64-bit. Depends on RV32/64
    X17             = 0x1011 # 32/64-bit. Depends on RV32/64
    X18             = 0x1012 # 32/64-bit. Depends on RV32/64
    X19             = 0x1013 # 32/64-bit. Depends on RV32/64
    X20             = 0x1014 # 32/64-bit. Depends on RV32/64
    X21             = 0x1015 # 32/64-bit. Depends on RV32/64
    X22             = 0x1016 # 32/64-bit. Depends on RV32/64
    X23             = 0x1017 # 32/64-bit. Depends on RV32/64
    X24             = 0x1018 # 32/64-bit. Depends on RV32/64
    X25             = 0x1019 # 32/64-bit. Depends on RV32/64
    X26             = 0x101A # 32/64-bit. Depends on RV32/64
    X27             = 0x101B # 32/64-bit. Depends on RV32/64
    X28             = 0x101C # 32/64-bit. Depends on RV32/64
    X29             = 0x101D # 32/64-bit. Depends on RV32/64
    X30             = 0x101E # 32/64-bit. Depends on RV32/64
    X31             = 0x101F # 32/64-bit. Depends on RV32/64
    
    F0              = 0x1020 # Length depends on length of floating point unit
    F1              = 0x1021 # Length depends on length of floating point unit
    F2              = 0x1022 # Length depends on length of floating point unit
    F3              = 0x1023 # Length depends on length of floating point unit
    F4              = 0x1024 # Length depends on length of floating point unit
    F5              = 0x1025 # Length depends on length of floating point unit
    F6              = 0x1026 # Length depends on length of floating point unit
    F7              = 0x1027 # Length depends on length of floating point unit
    F8              = 0x1028 # Length depends on length of floating point unit
    F9              = 0x1029 # Length depends on length of floating point unit
    F10             = 0x102A # Length depends on length of floating point unit
    F11             = 0x102B # Length depends on length of floating point unit
    F12             = 0x102C # Length depends on length of floating point unit
    F13             = 0x102D # Length depends on length of floating point unit
    F14             = 0x102E # Length depends on length of floating point unit
    F15             = 0x102F # Length depends on length of floating point unit
    F16             = 0x1020 # Length depends on length of floating point unit
    F17             = 0x1031 # Length depends on length of floating point unit
    F18             = 0x1032 # Length depends on length of floating point unit
    F19             = 0x1033 # Length depends on length of floating point unit
    F20             = 0x1034 # Length depends on length of floating point unit
    F21             = 0x1035 # Length depends on length of floating point unit
    F22             = 0x1036 # Length depends on length of floating point unit
    F23             = 0x1037 # Length depends on length of floating point unit
    F24             = 0x1038 # Length depends on length of floating point unit
    F25             = 0x1039 # Length depends on length of floating point unit
    F26             = 0x103A # Length depends on length of floating point unit
    F27             = 0x103B # Length depends on length of floating point unit
    F28             = 0x103C # Length depends on length of floating point unit
    F29             = 0x103D # Length depends on length of floating point unit
    F30             = 0x103E # Length depends on length of floating point unit
    F31             = 0x103F # Length depends on length of floating point unit
    
    V0              = 0x1040 # Length = ???
    V1              = 0x1041 # Length = ???
    V2              = 0x1042 # Length = ???
    V3              = 0x1043 # Length = ???
    V4              = 0x1044 # Length = ???
    V5              = 0x1045 # Length = ???
    V6              = 0x1046 # Length = ???
    V7              = 0x1047 # Length = ???
    V8              = 0x1048 # Length = ???
    V9              = 0x1049 # Length = ???
    V10             = 0x104A # Length = ???
    V11             = 0x104B # Length = ???
    V12             = 0x104C # Length = ???
    V13             = 0x104D # Length = ???
    V14             = 0x104E # Length = ???
    V15             = 0x104F # Length = ???
    V16             = 0x1050 # Length = ???
    V17             = 0x1051 # Length = ???
    V18             = 0x1052 # Length = ???
    V19             = 0x1053 # Length = ???
    V20             = 0x1054 # Length = ???
    V21             = 0x1055 # Length = ???
    V22             = 0x1056 # Length = ???
    V23             = 0x1057 # Length = ???
    V24             = 0x1058 # Length = ???
    V25             = 0x1059 # Length = ???
    V26             = 0x105A # Length = ???
    V27             = 0x105B # Length = ???
    V28             = 0x105C # Length = ???
    V29             = 0x105D # Length = ???
    V30             = 0x105E # Length = ???
    V31             = 0x105F # Length = ???
    VP0             = 0x1060 # Length = ???
    VP1             = 0x1061 # Length = ???
    VP2             = 0x1062 # Length = ???
    VP3             = 0x1063 # Length = ???
    VP4             = 0x1064 # Length = ???
    VP5             = 0x1065 # Length = ???
    VP6             = 0x1066 # Length = ???
    VP7             = 0x1067 # Length = ???
    
    PC              = 0x1080 # 32/64-bit. Depends on RV32/64