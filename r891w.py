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

import Ui_r891w
#if hasattr(Qt, 'AA_EnableHighDpiScaling'):
PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
 
#if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

#form_class = uic.loadUiType("r891w.ui")[0]

#class XDialog(QDialog, form_class):
class XDialog(QDialog , Ui_r891w.Ui_Dialog):
	sigStartEndTime = QtCore.pyqtSignal(str,str)
	def __init__(self):
		QDialog.__init__(self)
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
		sFmTime = (datetime.datetime.strptime( dRadio891Data['schedule_table'][i]['sTime'] , '%H%M%S' ) - datetime.timedelta(minutes=4)).strftime('%H%M%S')
		sToTime = (datetime.datetime.strptime( dRadio891Data['schedule_table'][i]['eTime'] , '%H%M%S' ) - datetime.timedelta(minutes=3)).strftime('%H%M%S')
		self.checkBox_Open.setChecked( True if( dRadio891Data['schedule_table'][i]['opnYn'] == 'Y' ) else False )
		self.timeEdit_StartTm.setTime( time( int(sFmTime[0:2]),int(sFmTime[2:4]),int(sFmTime[4:6]) ))
		self.timeEdit_EndTm  .setTime( time( int(sToTime[0:2]),int(sToTime[2:4]),int(sToTime[4:6]) ))
		self.lineEdit_FileName.setText( datetime.datetime.now().strftime('%y%m%d') + '_' + sFmTime + ' ' + dRadio891Data['schedule_table'][i]['title'] + ( '.mp4' if( dRadio891Data['schedule_table'][i]['opnYn'] == 'Y' ) else '.m4a' ) )

	def tryRecording(self):
		self.pushButton_Start.setEnabled(False)
		self.pushButton_Stop.setEnabled(True)

		self.progressBar.setRange(0,100)
		self.sigStartEndTime.emit( self.timeEdit_StartTm.time().toString('hhmmss') , self.timeEdit_EndTm.time().toString('hhmmss') )
		self.thdRecording.start()

	def stopRecording(self,tp):
		if tp == 'EndRec' :
			QMessageBox.about(self, ' ' , "녹화가 완료되었습니다.")
		else :
			if QMessageBox.question(self,' ', '녹화를 중지하시겠습니까?', QMessageBox.Yes | QMessageBox.No ) == QMessageBox.No :
				self.progressBar.setValue(0)
				return
			os.system('TASKKILL /F /IM ffmpeg.exe /T')

		self.pushButton_Start.setEnabled(True)
		self.pushButton_Stop.setEnabled(False)
		if self.thdRecording.isRunning():  # 쓰레드가 돌아가고 있다면 
			self.thdRecording.woring = False
			self.thdRecording.terminate()  # 현재 돌아가는 thread 를 중지시킨다
			self.thdRecording.wait()       # 새롭게 thread를 대기한후

	@QtCore.pyqtSlot(str,int)
	def progressStatus(self,tp,persents):
		print("프로그레스바 진행률 표시 등등 스레드의 정보(진행상태:%s,퍼센트:%d)" % (tp, persents ))
		self.progressBar.setValue(persents)
		if tp == 'EndRec' :
			self.stopRecording(tp)


class worker(QtCore.QThread):
	progressInfoChanged = QtCore.pyqtSignal(str,int)
	sSttTm = '000000'
	sEndTm = '001000'
	def __init__(self, parent=XDialog):
		super().__init__()
		self.main = parent
#		self.working = True

	def __del__(self):
		print(".... end thread.....")
		self.wait()

	def run(self):
		self.progressInfoChanged.emit('waiting',5)
		sCurrentTime = r891d.WaitingForRecord( worker.sSttTm , worker.sEndTm )

		self.progressInfoChanged.emit('getInfo',25)
		dRadio891Data = r891d.GetRadioSchedule( worker.sSttTm , worker.sEndTm , 1 )
		print (dRadio891Data)
		self.progressInfoChanged.emit('startRec',45)
		r891d.RecodingRadio(  worker.sSttTm , worker.sEndTm  , sCurrentTime , dRadio891Data )

		self.progressInfoChanged.emit('EndRec',65)
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

	rec_stt_time = r891d.CFG_REC_STT_TIME
	rec_end_time = r891d.CFG_REC_END_TIME

	dRadio891Data = r891d.GetRadioSchedule( rec_stt_time , rec_end_time , 0 )
	if dRadio891Data == False :
		exit(0)
	app = QApplication(sys.argv)
	dialog = XDialog()
	dialog.show()
	app.exec_()
