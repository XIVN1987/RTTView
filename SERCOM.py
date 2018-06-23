#coding: utf-8
''' 升级记录
'''
import sys, os, re
import ConfigParser
import ctypes, struct
import threading, time

import sip
sip.setapi('QString', 2)
from PyQt4 import QtCore, QtGui, uic

import PyQt4.Qwt5 as Qwt
from PyQt4.Qwt5 import QwtPlot

class RingBuffer(object):
    def __init__(self, arr):
        self.sName, self.pBuffer, self.SizeOfBuffer, self.WrOff, self.RdOff, self.Flags = arr
    
    def __str__(self):
        return 'Buffer Address = 0x%08X\nBuffer Size    = %d\nWrite Offset   = %d\nRead Offset    = %d\n' %(self.pBuffer, self.SizeOfBuffer, self.WrOff, self.RdOff)

class SERCOM(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SERCOM, self).__init__(parent)
        
        uic.loadUi('SERCOM.ui', self)
        
        self.on_cmbMode_currentIndexChanged(u'文本')
        
        self.initSetting()
        self.initQwtPlot()
        
        self.closed = False
        threading.Thread(target=self.serial_recv).start()
    
    def initQwtPlot(self):
        self.PlotBuff = ''
        self.PlotData = [0]*1000
        
        self.PlotCurve = Qwt.QwtPlotCurve()
        self.PlotCurve.attach(self.qwtPlot)
        self.PlotCurve.setData(range(1, len(self.PlotData)+1), self.PlotData)
    
    def initSetting(self):
        if not os.path.exists('setting.ini'):
            open('setting.ini', 'w')
        
        self.conf = ConfigParser.ConfigParser()
        self.conf.read('setting.ini')
        
        if not self.conf.has_section('globals'):
            self.conf.add_section('globals')
            self.conf.set('globals', 'dllpath', ' ')
            self.conf.set('globals', 'mappath', ' ')
        self.linDLL.setText(self.conf.get('globals', 'dllpath').decode('gbk'))
        self.linMap.setText(self.conf.get('globals', 'mappath').decode('gbk'))
    
    @QtCore.pyqtSlot()
    def on_btnDLL_clicked(self):
        path = QtGui.QFileDialog.getOpenFileName(caption=u'JLinkARM.dll路径')
        if path != '':
            self.linDLL.setText(path)
    
    @QtCore.pyqtSlot()
    def on_btnMap_clicked(self):
        path = QtGui.QFileDialog.getOpenFileName(caption=u'项目.map文件路径')
        if path != '':
            self.linMap.setText(path)
    
    def parseRTTAddr(self):
        with open(self.linMap.text(), 'r') as f:
            for line in f:
                match = re.match('\s+_SEGGER_RTT\s+(0x[0-9a-fA-F]{8})\s+Data.+', line)
                if match:
                    break
        if match:
            return int(match.group(1), 16)
        else:
            return 0x20000000
    
    @QtCore.pyqtSlot()
    def on_btnOpen_clicked(self):
        if self.btnOpen.text() == u'打开连接':
            try:
                self.jlink = ctypes.cdll.LoadLibrary(self.linDLL.text())
                self.jlink.JLINKARM_TIF_Select(1)
                
                self.RTTAddr = self.parseRTTAddr()
            except Exception as ex:
                print ex
            else:
                self.btnOpen.setText(u'关闭连接')
                self.lblStat.setPixmap(QtGui.QPixmap("./Image/inopening.png"))
        else:
            self.btnOpen.setText(u'打开连接')
            self.lblStat.setPixmap(QtGui.QPixmap("./Image/inclosing.png"))
            
            self.jlink.JLINKARM_Close()
    
    def aUpEmpty(self):
        LEN = (16 + 4*2) + (4*6) * 4
        
        buf = ctypes.create_string_buffer(LEN)
        
        self.jlink.JLINKARM_ReadMem(self.RTTAddr, LEN, buf)
        
        arr = struct.unpack('16sLLLLLLLL24xLLLLLL24x', buf.raw)
        
        self.aUp = RingBuffer(arr[3:9])

        print 'WrOff=%d, RdOff=%d' %(self.aUp.WrOff, self.aUp.RdOff)
        
        self.aDown = RingBuffer(arr[9:15])
        
        return (self.aUp.RdOff == self.aUp.WrOff)
    
    def aUpRead(self):
        if self.aUp.RdOff < self.aUp.WrOff:
            len = self.aUp.WrOff - self.aUp.RdOff
            
            str = ctypes.create_string_buffer(len)
            
            self.jlink.JLINKARM_ReadMem(self.aUp.pBuffer + self.aUp.RdOff, len, str)
            
            self.aUp.RdOff += len
            
            buf = ctypes.create_string_buffer(struct.pack('L', self.aUp.RdOff))
            self.jlink.JLINKARM_WriteMem(self.RTTAddr + (16 + 4*2) + 4*4, 4, buf)
        else:
            len = self.aUp.SizeOfBuffer - self.aUp.RdOff + 1
            
            str = ctypes.create_string_buffer(len)
            
            self.jlink.JLINKARM_ReadMem(self.aUp.pBuffer + self.aUp.RdOff, len, str)
            
            self.aUp.RdOff = 0  #这样下次再读就会进入执行上个条件
            
            buf = ctypes.create_string_buffer(struct.pack('L', self.aUp.RdOff))
            self.jlink.JLINKARM_WriteMem(self.RTTAddr + (16 + 4*2) + 4*4, 4, buf)            
        
        return str.raw
    
    received = QtCore.pyqtSignal(str)
    def serial_recv(self):
        self.received.connect(self.on_received)
        
        buffer = ''
        while not self.closed:
            if self.btnOpen.text() == u'关闭连接':
                if not self.aUpEmpty():
                    self.received.emit(self.aUpRead())
            
            time.sleep(0.01)
    
    def on_received(self, str): #注意，虽然定义信号时用的参数类型是str，但PyQt传递参数是当作unicode传递的
        if self.mode == u'文本':
            if len(self.txtMain.toPlainText()) > 25000: self.txtMain.clear()
            self.txtMain.moveCursor(QtGui.QTextCursor.End)
            self.txtMain.insertPlainText(str)
            
        elif self.mode == u'波形':
            self.PlotBuff += str
            if self.PlotBuff.rfind(',') == -1: return
            try:
                d = [int(x) for x in self.PlotBuff[0:self.PlotBuff.rfind(',')].split(',')]
                for x in d:
                    self.PlotData.pop(0)
                    self.PlotData.append(x)        
            except:
                self.PlotBuff = ''
            else:
                self.PlotBuff = self.PlotBuff[self.PlotBuff.rfind(',')+1:]
            
            self.PlotCurve.setData(range(1, len(self.PlotData)+1), self.PlotData)
            self.qwtPlot.replot()
    
    @QtCore.pyqtSlot(str)
    def on_cmbMode_currentIndexChanged(self, str):
        self.mode = str
        self.txtMain.setVisible(self.mode == u'文本')
        self.qwtPlot.setVisible(self.mode == u'波形')
    
    @QtCore.pyqtSlot()
    def on_btnClear_clicked(self):
        self.txtMain.clear()
    
    def closeEvent(self, evt):
        self.closed = True
        
        self.conf.set('globals', 'dllpath', self.linDLL.text().encode('gbk'))
        self.conf.set('globals', 'mappath', self.linMap.text().encode('gbk'))
        self.conf.write(open('setting.ini', 'w'))
        
        if hasattr(self, 'jlink') and self.jlink.JLINKARM_IsOpen():
            self.jlink.JLINKARM_Close()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ser = SERCOM()
    ser.show()
    app.exec_()