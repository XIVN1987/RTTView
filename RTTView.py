#! python2
#coding: utf-8
import os
import sys
import ctypes
import struct
import ConfigParser

import sip
sip.setapi('QString', 2)
from PyQt4 import QtCore, QtGui, uic
from PyQt4.Qwt5 import QwtPlot, QwtPlotCurve


class RingBuffer(object):
    def __init__(self, arr):
        self.sName, self.pBuffer, self.SizeOfBuffer, self.WrOff, self.RdOff, self.Flags = arr
    
    def __str__(self):
        return 'Buffer Address = 0x%08X\nBuffer Size    = %d\nWrite Offset   = %d\nRead Offset    = %d\n' %(self.pBuffer, self.SizeOfBuffer, self.WrOff, self.RdOff)


'''
from RTTView_UI import Ui_RTTView
class RTTView(QtGui.QWidget, Ui_RTTView):
    def __init__(self, parent=None):
        super(RTTView, self).__init__(parent)
        
        self.setupUi(self)
'''
class RTTView(QtGui.QWidget):
    def __init__(self, parent=None):
        super(RTTView, self).__init__(parent)
        
        uic.loadUi('RTTView.ui', self)

        self.initSetting()

        self.initQwtPlot()
        
        self.tmrRTT = QtCore.QTimer()
        self.tmrRTT.setInterval(10)
        self.tmrRTT.timeout.connect(self.on_tmrRTT_timeout)
        self.tmrRTT.start()
    
    def initSetting(self):
        if not os.path.exists('setting.ini'):
            open('setting.ini', 'w')
        
        self.conf = ConfigParser.ConfigParser()
        self.conf.read('setting.ini')
        
        if not self.conf.has_section('J-Link'):
            self.conf.add_section('J-Link')
            self.conf.set('J-Link', 'dllpath', '')
            self.conf.add_section('Memory')
            self.conf.set('Memory', 'StartAddr', '0x20000000')

        self.linDLL.setText(self.conf.get('J-Link', 'dllpath').decode('gbk'))
        self.linAddr.setText(self.conf.get('Memory', 'StartAddr'))

    def initQwtPlot(self):
        self.PlotBuff = ''
        self.PlotData = [0]*1000
        
        self.qwtPlot = QwtPlot(self)
        self.vLayout0.insertWidget(0, self.qwtPlot)
        
        self.PlotCurve = QwtPlotCurve()
        self.PlotCurve.attach(self.qwtPlot)
        self.PlotCurve.setData(range(1, len(self.PlotData)+1), self.PlotData)

        self.on_cmbMode_currentIndexChanged(u'文本显示')
    
    @QtCore.pyqtSlot()
    def on_btnOpen_clicked(self):
        if self.btnOpen.text() == u'打开连接':
            try:
                self.jlink = ctypes.cdll.LoadLibrary(self.linDLL.text())

                err_buf = (ctypes.c_char * 64)()
                self.jlink.JLINKARM_ExecCommand('Device = Cortex-M0', err_buf, 64)

                self.jlink.JLINKARM_TIF_Select(1)
                self.jlink.JLINKARM_SetSpeed(8000)
                
                buff = ctypes.create_string_buffer(1024)
                Addr = int(self.linAddr.text(), 16)
                for i in range(256):
                    self.jlink.JLINKARM_ReadMem(Addr + 1024*i, 1024, buff)
                    index = buff.raw.find('SEGGER RTT')
                    if index != -1:
                        self.RTTAddr = Addr + 1024*i + index
                        print '_SEGGER_RTT @ 0x%08X' %self.RTTAddr
                        break
                else:
                    raise Exception('Can not find _SEGGER_RTT')
            except Exception as e:
                print e
            else:
                self.btnOpen.setText(u'关闭连接')
                self.lblStat.setPixmap(QtGui.QPixmap("./Image/inopening.png"))
        else:
            self.btnOpen.setText(u'打开连接')
            self.lblStat.setPixmap(QtGui.QPixmap("./Image/inclosing.png"))
            
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
    
    def on_tmrRTT_timeout(self):
        if self.btnOpen.text() == u'关闭连接':
            if not self.aUpEmpty():
                str = self.aUpRead()
                
                if self.mode == u'文本显示':
                    if len(self.txtMain.toPlainText()) > 25000: self.txtMain.clear()
                    self.txtMain.moveCursor(QtGui.QTextCursor.End)
                    self.txtMain.insertPlainText(str)
                    
                elif self.mode == u'波形显示':
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
        self.txtMain.setVisible(self.mode == u'文本显示')
        self.qwtPlot.setVisible(self.mode == u'波形显示')
    
    @QtCore.pyqtSlot()
    def on_btnDLL_clicked(self):
        path = QtGui.QFileDialog.getOpenFileName(caption=u'JLinkARM.dll路径', filter=u'动态链接库文件 (*.dll)', directory=self.linDLL.text())
        if path != '':
            self.linDLL.setText(path)

    @QtCore.pyqtSlot()
    def on_btnClear_clicked(self):
        self.txtMain.clear()
    
    def closeEvent(self, evt):
        self.conf.set('J-Link', 'dllpath', self.linDLL.text().encode('gbk'))
        self.conf.set('Memory', 'StartAddr', self.linAddr.text())
        self.conf.write(open('setting.ini', 'w'))
        

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    rtt = RTTView()
    rtt.show()
    app.exec_()
