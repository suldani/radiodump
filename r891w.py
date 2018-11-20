#!/opt/bin/python
# -*- coding: utf-8 -*-
#####################################################################
# pip install requests
# pip install pytz
# pip install pyinstaller
# pyinstaller --i=coolfm.ico -F r891d.py
#####################################################################
import sys
import requests
import json
import datetime
import time
import os
import shutil
import logging
import logging.handlers
import r891d  #  import init_log, init_cfg, get_pgm_info, rec_kbs_radio
import PyQt5

from pytz            import timezone
from datetime        import time
from PyQt5           import uic, QtCore
from PyQt5.QtWidgets import *

#import Ui_r891w
#if hasattr(Qt, 'AA_EnableHighDpiScaling'):
PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
 
#if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

form_class = uic.loadUiType("r891w.ui")[0]

class XDialog(QDialog, form_class):
#class XDialog(QDialog , Ui_r891w.Ui_Dialog):
	sigStartEndTime = QtCore.pyqtSignal(str,str)
#	zerotime        = QtCore.QTime(00,00,00)
#	self.progressTp = ''
#	self.nMaxValue  = 100

	def __init__(self):
		QDialog.__init__(self)
		self.timer    = QtCore.QTimer(self)
		self.timer.timeout.connect(self.changeProgressStatus)
		# setupUi() 메서드는 화면에 다이얼로그 보여줌
		self.setupUi(self)

		for i in range( len( dRadio891Data['schedule_table'] ) ) :
			self.comboBox_Schedule.addItem( dRadio891Data['schedule_table'][i]['sTime'][:2] + '~' + dRadio891Data['schedule_table'][i]['eTime'][:2] + "시 "+ ( '*' if( dRadio891Data['schedule_table'][i]['opnYn'] == 'Y' ) else '' ) + dRadio891Data['schedule_table'][i]['title'] )

		# custom signal from worker thread to main thread
		self.thdRecording = worker()
		self.thdRecording.progressInfoChanged.connect(self.progressStatus)

		# custom signal from main thread to worker thread
		self.sigStartEndTime.connect(self.thdRecording.thdTryRecording)

	def setRecInfo(self,i):
		r891d.CFG_PROGRAM_STIME = dRadio891Data['schedule_table'][i]['sTime']
		sFmTime = (datetime.datetime.strptime( dRadio891Data['schedule_table'][i]['sTime'] , '%H%M%S' ) - datetime.timedelta(minutes=4)).strftime('%H%M%S')
		sToTime = (datetime.datetime.strptime( dRadio891Data['schedule_table'][i]['eTime'] , '%H%M%S' ) - datetime.timedelta(minutes=3)).strftime('%H%M%S')
		self.checkBox_Open.setChecked( True if( dRadio891Data['schedule_table'][i]['opnYn'] == 'Y' ) else False )
		self.timeEdit_StartTm.setTime( time( int(sFmTime[0:2]),int(sFmTime[2:4]),int(sFmTime[4:6]) ))
		self.timeEdit_EndTm  .setTime( time( int(sToTime[0:2]),int(sToTime[2:4]),int(sToTime[4:6]) ))
		self.lineEdit_FileName.setText( datetime.datetime.now().strftime('%y%m%d') + '_' + sFmTime + ' ' + dRadio891Data['schedule_table'][i]['title'] + ( '.mp4' if( dRadio891Data['schedule_table'][i]['opnYn'] == 'Y' ) else '.m4a' ) + '(예정)')

	def tryRecording(self):
		self.pushButton_Start.setEnabled(False)
		self.pushButton_Stop.setEnabled(True)

		self.progressBar.setRange(0,100)
		self.sigStartEndTime.emit( self.timeEdit_StartTm.time().toString('hhmmss') , self.timeEdit_EndTm.time().toString('hhmmss') )
		self.thdRecording.start()

	def stopRecording(self,tp):
		if QMessageBox.question(self,' ', '녹화를 중지하시겠습니까?', QMessageBox.Yes | QMessageBox.No ) == QMessageBox.No :
			return
		os.system('TASKKILL /F /IM ffmpeg.exe /T')
		self.pushButton_Start.setEnabled(True)
		self.pushButton_Stop.setEnabled(False)


	@QtCore.pyqtSlot(str,int)
	def progressStatus(self,tp,nMaxValue):
		print("프로그레스바 진행률 표시 등등 스레드의 정보(진행상태:%s,퍼센트:%d)" % (tp, nMaxValue ))
#		progressTp = tp
#		nMaxValue  = nMaxValue

		self.progressBar.setMaximum( nMaxValue )
		self.progressBar.setRange(0, nMaxValue )
		self.lineEdit_FileName.setText( dRadio891Data['strm_flnm'] )
		if tp == 'waiting' :
			self.progressBar.setValue( 0 )
			self.progressBar.setFormat('%p% / 대기중(%02d:%02d:%02d)' % ( nMaxValue/3600, nMaxValue%3600/60 ,nMaxValue%60 ) )
		elif tp == 'startRec' :
			self.progressBar.setFormat('%p% / 녹화중(00:00:00)')
			self.zerotime = QtCore.QTime(00,00,00)
			self.timer.start(1000)
		elif tp == 'EndRec' :
			self.timer.stop()
			self.progressBar.setFormat('%p% / 완료(%v)')
#			self.progressBar.setValue(100)
#			self.progressBar.setRange(0,100)
			self.pushButton_Start.setEnabled(True)
			self.pushButton_Stop.setEnabled(False)
			os.system('TASKKILL /F /IM ffmpeg.exe /T')
			if self.thdRecording.isRunning():  # 쓰레드가 돌아가고 있다면 
				self.thdRecording.woring = False
				self.thdRecording.terminate()  # 현재 돌아가는 thread 를 중지시킨다
				self.thdRecording.wait()       # 새롭게 thread를 대기한후

			QMessageBox.about(self, ' ' , "녹화가 완료되었습니다.")


	def changeProgressStatus(self):
		self.zerotime = self.zerotime.addSecs(1)
		self.progressBar.setValue( QtCore.QTime(0, 0, 0).secsTo(self.zerotime) )
		self.progressBar.setFormat('%p% / 녹화중('+ self.zerotime.toString("hh:mm:ss") + ')')


class worker(QtCore.QThread):
	progressInfoChanged = QtCore.pyqtSignal(str,int)
	sSttTm = '000000'
	sEndTm = '001000'
	def __init__(self, parent=XDialog):
		super().__init__()
		self.main = parent

	def __del__(self):
		print(".... end thread.....")
		self.wait()

	def run(self):
		while True :
			dWRtn = r891d.WaitingForRecord( worker.sSttTm , worker.sEndTm )
			if dWRtn['nSleepTime'] > 0 :
				r891d.logger.info( "Waiting [%5d] seconds... ( Start[%6s] End[%6s] Now[%6s] )" , dWRtn['nSleepTime'] , r891d.CFG_REC_STT_TIME , r891d.CFG_REC_END_TIME , dWRtn['sCurrentTime'] )
				self.progressInfoChanged.emit('waiting',int(dWRtn['nSleepTime']))
				self.sleep( r891d.CFG_HB_MIN*60 if( dWRtn['nSleepTime'] > r891d.CFG_HB_MIN*60 ) else dWRtn['nSleepTime'] )
			else :
				break

		dRadio891Data = r891d.GetRadioScheduleAndReady( worker.sSttTm , worker.sEndTm , True )
		self.progressInfoChanged.emit('startRec',int(dRadio891Data['strm_time']))
		if r891d.StartRecording(  dRadio891Data['strm_call'] , dRadio891Data['strm_flnm'] ) < 0 :
			print('녹화중 에러났음')
			self.working = False

		self.progressInfoChanged.emit('EndRec',int(dRadio891Data['strm_time']))
		self.working = False

	@QtCore.pyqtSlot( str, str )
	def thdTryRecording(self, a , b ):
		worker.sSttTm = a
		worker.sEndTm = b


if __name__ == "__main__":
	# 환경설정
	r891d.logger = r891d.init_log(True,True) # 파일,화면
	r891d.logger.info( "=============================== Start ===============================" )

	# 환경설정
	r891d.init_cfg(os.path.splitext(sys.argv[0])[0] + '.json')

	dRadio891Data = r891d.GetRadioScheduleAndReady( r891d.CFG_REC_STT_TIME , r891d.CFG_REC_END_TIME , False )
	if dRadio891Data == False :
		exit(0)
	app = QApplication(sys.argv)
	dialog = XDialog()
	dialog.show()
	app.exec_()
