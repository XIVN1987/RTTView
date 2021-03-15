#! python3
import os
import sys
import time
import ctypes
import configparser

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QLegend


N_CURVES = 4

class RingBuffer(ctypes.Structure):
    _fields_ = [
        ('sName',        ctypes.c_uint),    # ctypes.POINTER(ctypes.c_char)，64位Python中 ctypes.POINTER 是64位的，与目标芯片不符
        ('pBuffer',      ctypes.c_uint),    # ctypes.POINTER(ctypes.c_byte)
        ('SizeOfBuffer', ctypes.c_uint),
        ('WrOff',        ctypes.c_uint),    # Position of next item to be written. 对于aUp：   芯片更新WrOff，主机更新RdOff
        ('RdOff',        ctypes.c_uint),    # Position of next item to be read.    对于aDown： 主机更新WrOff，芯片更新RdOff
        ('Flags',        ctypes.c_uint),
    ]

class SEGGER_RTT_CB(ctypes.Structure):      # Control Block
    _fields_ = [
        ('acID',              ctypes.c_char * 16),
        ('MaxNumUpBuffers',   ctypes.c_uint),
        ('MaxNumDownBuffers', ctypes.c_uint),
        ('aUp',               RingBuffer * 2),
        ('aDown',             RingBuffer * 2),
    ]


'''
from RTTView_UI import Ui_RTTView
class RTTView(QWidget, Ui_RTTView):
    def __init__(self, parent=None):
        super(RTTView, self).__init__(parent)
        
        self.setupUi(self)
'''
class RTTView(QWidget):
    def __init__(self, parent=None):
        super(RTTView, self).__init__(parent)
        
        uic.loadUi('RTTView.ui', self)

        self.initSetting()

        self.initQwtPlot()

        self.rcvbuff = b''
        
        self.tmrRTT = QtCore.QTimer()
        self.tmrRTT.setInterval(10)
        self.tmrRTT.timeout.connect(self.on_tmrRTT_timeout)
        self.tmrRTT.start()

        self.tmrRTT_Cnt = 0
    
    def initSetting(self):
        if not os.path.exists('setting.ini'):
            open('setting.ini', 'w', encoding='utf-8')
        
        self.conf = configparser.ConfigParser()
        self.conf.read('setting.ini', encoding='utf-8')
        
        if not self.conf.has_section('J-Link'):
            self.conf.add_section('J-Link')
            self.conf.set('J-Link', 'dllpath', '')
            self.conf.set('J-Link', 'mcucore', 'Cortex-M0')
            self.conf.add_section('Memory')
            self.conf.set('Memory', 'rttaddr', '0x20000000')

        self.linDLL.setText(self.conf.get('J-Link', 'dllpath'))
        self.linRTT.setText(self.conf.get('Memory', 'rttaddr'))
        self.cmbCore.setCurrentIndex(self.cmbCore.findText(self.conf.get('J-Link', 'mcucore')))

    def initQwtPlot(self):
        self.PlotData  = [[0]*1000 for i in range(N_CURVES)]
        self.PlotPoint = [[QtCore.QPointF(j, 0) for j in range(1000)] for i in range(N_CURVES)]

        self.PlotChart = QChart()

        self.ChartView = QChartView(self.PlotChart)
        self.ChartView.setVisible(False)
        self.vLayout.insertWidget(0, self.ChartView)
        
        self.PlotCurve = [QLineSeries() for i in range(N_CURVES)]
    
    @pyqtSlot()
    def on_btnOpen_clicked(self):
        if self.btnOpen.text() == '打开连接':
            try:
                self.jlink = ctypes.cdll.LoadLibrary(self.linDLL.text())

                err_buf = (ctypes.c_char * 64)()
                self.jlink.JLINKARM_ExecCommand(f'Device = {self.cmbCore.currentText()}'.encode('latin-1'), err_buf, 64)

                self.jlink.JLINKARM_TIF_Select(1)
                self.jlink.JLINKARM_SetSpeed(4000)
                
                buff = ctypes.create_string_buffer(1024)
                Addr = int(self.linRTT.text(), 16)
                for i in range(128):
                    self.jlink.JLINKARM_ReadMem(Addr + 1024*i, 1024, buff)
                    index = buff.raw.find(b'SEGGER RTT')
                    if index != -1:
                        self.RTTAddr = Addr + 1024*i + index

                        buff = ctypes.create_string_buffer(ctypes.sizeof(SEGGER_RTT_CB))
                        self.jlink.JLINKARM_ReadMem(self.RTTAddr, ctypes.sizeof(SEGGER_RTT_CB), buff)

                        rtt_cb = SEGGER_RTT_CB.from_buffer(buff)
                        self.aUpAddr = self.RTTAddr + 16 + 4 + 4
                        self.aDownAddr = self.aUpAddr + ctypes.sizeof(RingBuffer) * rtt_cb.MaxNumUpBuffers

                        self.txtMain.append(f'\n_SEGGER_RTT @ 0x{self.RTTAddr:08X} with {rtt_cb.MaxNumUpBuffers} aUp and {rtt_cb.MaxNumDownBuffers} aDown\n')
                        break
                else:
                    raise Exception('Can not find _SEGGER_RTT')
            except Exception as e:
                self.txtMain.append(f'\n{str(e)}\n')
            else:
                self.linDLL.setEnabled(False)
                self.btnDLL.setEnabled(False)
                self.linRTT.setEnabled(False)
                self.cmbCore.setEnabled(False)
                self.btnOpen.setText('关闭连接')
        else:
            self.linDLL.setEnabled(True)
            self.btnDLL.setEnabled(True)
            self.linRTT.setEnabled(True)
            self.cmbCore.setEnabled(True)
            self.btnOpen.setText('打开连接')
    
    def aUpRead(self):
        buf = ctypes.create_string_buffer(ctypes.sizeof(RingBuffer))
        self.jlink.JLINKARM_ReadMem(self.aUpAddr, ctypes.sizeof(RingBuffer), buf)

        aUp = RingBuffer.from_buffer(buf)
        
        if aUp.RdOff == aUp.WrOff:
            str = ctypes.create_string_buffer(0)

        elif aUp.RdOff < aUp.WrOff:
            cnt = aUp.WrOff - aUp.RdOff
            str = ctypes.create_string_buffer(cnt)
            self.jlink.JLINKARM_ReadMem(ctypes.cast(aUp.pBuffer, ctypes.c_void_p).value + aUp.RdOff, cnt, str)
            
            aUp.RdOff += cnt
            
            self.jlink.JLINKARM_WriteU32(self.aUpAddr + 4*4, aUp.RdOff)

        else:
            cnt = aUp.SizeOfBuffer - aUp.RdOff
            str = ctypes.create_string_buffer(cnt)
            self.jlink.JLINKARM_ReadMem(ctypes.cast(aUp.pBuffer, ctypes.c_void_p).value + aUp.RdOff, cnt, str)
            
            aUp.RdOff = 0  #这样下次再读就会进入执行上个条件
            
            self.jlink.JLINKARM_WriteU32(self.aUpAddr + 4*4, aUp.RdOff)
        
        return str.raw
    
    def on_tmrRTT_timeout(self):
        if self.btnOpen.text() == '关闭连接':
            try:
                self.rcvbuff += self.aUpRead()
                
                if self.txtMain.isVisible():
                    if self.chkHEXShow.isChecked():
                        text = ''.join(f'{x:02X} ' for x in self.rcvbuff)

                    else:
                        text = self.rcvbuff.decode('latin')

                    if len(self.txtMain.toPlainText()) > 25000: self.txtMain.clear()
                    self.txtMain.moveCursor(QtGui.QTextCursor.End)
                    self.txtMain.insertPlainText(text)

                    self.rcvbuff = b''

                else:
                    if self.rcvbuff.rfind(b',') == -1: return
                    
                    d = self.rcvbuff[0:self.rcvbuff.rfind(b',')].split(b',')    # [b'12', b'34'] or [b'12 34', b'56 78']
                    d = [[float(x) for x in X.strip().split()] for X in d]      # [[12], [34]]   or [[12, 34], [56, 78]]
                    for arr in d:
                        for i, x in enumerate(arr):
                            if i == N_CURVES: break

                            self.PlotData[i].pop(0)
                            self.PlotData[i].append(x)
                            self.PlotPoint[i].pop(0)
                            self.PlotPoint[i].append(QtCore.QPointF(999, x))
                    
                    self.rcvbuff = self.rcvbuff[self.rcvbuff.rfind(b',')+1:]

                    self.tmrRTT_Cnt += 1
                    if self.tmrRTT_Cnt % 4 == 0:
                        if len(d[-1]) != len(self.PlotChart.series()):
                            for series in self.PlotChart.series():
                                self.PlotChart.removeSeries(series)
                            for i in range(min(len(d[-1]), N_CURVES)):
                                self.PlotCurve[i].setName(f'Curve {i+1}')
                                self.PlotChart.addSeries(self.PlotCurve[i])
                            self.PlotChart.createDefaultAxes()

                        for i in range(len(self.PlotChart.series())):
                            for j, point in enumerate(self.PlotPoint[i]):
                                point.setX(j)
                        
                            self.PlotCurve[i].replace(self.PlotPoint[i])
                    
                        miny = min([min(d) for d in self.PlotData[:len(self.PlotChart.series())]])
                        maxy = max([max(d) for d in self.PlotData[:len(self.PlotChart.series())]])
                        self.PlotChart.axisY().setRange(miny, maxy)
                        self.PlotChart.axisX().setRange(0000, 1000)
            
            except Exception as e:
                self.rcvbuff = b''
                print(str(e))   # 波形显示模式下 txtMain 不可见，因此错误信息不能显示在其上
    
    def aDownWrite(self, bytes):
        buf = ctypes.create_string_buffer(ctypes.sizeof(RingBuffer))
        self.jlink.JLINKARM_ReadMem(self.aDownAddr, ctypes.sizeof(RingBuffer), buf)

        aDown = RingBuffer.from_buffer(buf)
        
        if aDown.WrOff >= aDown.RdOff:
            if aDown.RdOff != 0: cnt = min(aDown.SizeOfBuffer - aDown.WrOff, len(bytes))
            else:                cnt = min(aDown.SizeOfBuffer - 1 - aDown.WrOff, len(bytes))    # 写入操作不能使得 aDown.WrOff == aDown.RdOff，以区分满和空
            str = ctypes.create_string_buffer(bytes[:cnt])
            self.jlink.JLINKARM_WriteMem(ctypes.cast(aDown.pBuffer, ctypes.c_void_p).value + aDown.WrOff, cnt, str)
            
            aDown.WrOff += cnt
            if aDown.WrOff == aDown.SizeOfBuffer: aDown.WrOff = 0

            bytes = bytes[cnt:]

        if bytes and aDown.RdOff != 0 and aDown.RdOff != 1:         # != 0 确保 aDown.WrOff 折返回 0，!= 1 确保有空间可写入
            cnt = min(aDown.RdOff - 1 - aDown.WrOff, len(bytes))    # - 1 确保写入操作不导致WrOff与RdOff指向同一位置
            str = ctypes.create_string_buffer(bytes[:cnt])
            self.jlink.JLINKARM_WriteMem(ctypes.cast(aDown.pBuffer, ctypes.c_void_p).value + aDown.WrOff, cnt, str)

            aDown.WrOff += cnt

        self.jlink.JLINKARM_WriteU32(self.aDownAddr + 4*3, aDown.WrOff)

    @pyqtSlot()
    def on_btnSend_clicked(self):
        if self.btnOpen.text() == '关闭连接':
            text = self.txtSend.toPlainText()

            try:
                if self.chkHEXSend.isChecked():
                    text = ''.join([chr(int(x, 16)) for x in text.split()])

                self.aDownWrite(text.encode('latin'))

            except Exception as e:
                self.txtMain.append(f'\n{str(e)}\n')

    @pyqtSlot()
    def on_btnDLL_clicked(self):
        dllpath, filter = QFileDialog.getOpenFileName(caption='JLink_x64.dll路径', filter='动态链接库文件 (*.dll)', directory=self.linDLL.text())
        if dllpath != '':
            self.linDLL.setText(dllpath)

    @pyqtSlot(int)
    def on_chkWavShow_stateChanged(self, state):
        self.ChartView.setVisible(state == Qt.Checked)
        self.txtMain.setVisible(state == Qt.Unchecked)

    @pyqtSlot()
    def on_btnClear_clicked(self):
        self.txtMain.clear()
    
    def closeEvent(self, evt):
        self.conf.set('J-Link', 'dllpath', self.linDLL.text())
        self.conf.set('J-Link', 'mcucore', self.cmbCore.currentText())
        self.conf.set('Memory', 'rttaddr', self.linRTT.text())
        self.conf.write(open('setting.ini', 'w', encoding='utf-8'))
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    rtt = RTTView()
    rtt.show()
    app.exec_()
