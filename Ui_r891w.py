# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'd:\Documents\radiodump\r891w.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setEnabled(True)
        Dialog.resize(492, 153)
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setGeometry(QtCore.QRect(0, 40, 491, 111))
        self.groupBox.setObjectName("groupBox")
        self.timeEdit_StartTm = QtWidgets.QTimeEdit(self.groupBox)
        self.timeEdit_StartTm.setEnabled(False)
        self.timeEdit_StartTm.setGeometry(QtCore.QRect(70, 20, 91, 21))
        self.timeEdit_StartTm.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.timeEdit_StartTm.setCalendarPopup(False)
        self.timeEdit_StartTm.setTime(QtCore.QTime(0, 0, 0))
        self.timeEdit_StartTm.setObjectName("timeEdit_StartTm")
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(10, 20, 51, 21))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.groupBox)
        self.label_3.setGeometry(QtCore.QRect(10, 50, 51, 21))
        self.label_3.setObjectName("label_3")
        self.timeEdit_EndTm = QtWidgets.QTimeEdit(self.groupBox)
        self.timeEdit_EndTm.setEnabled(False)
        self.timeEdit_EndTm.setGeometry(QtCore.QRect(240, 20, 91, 21))
        self.timeEdit_EndTm.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.timeEdit_EndTm.setCalendarPopup(False)
        self.timeEdit_EndTm.setTime(QtCore.QTime(0, 0, 0))
        self.timeEdit_EndTm.setObjectName("timeEdit_EndTm")
        self.label_5 = QtWidgets.QLabel(self.groupBox)
        self.label_5.setGeometry(QtCore.QRect(180, 20, 51, 21))
        self.label_5.setObjectName("label_5")
        self.lineEdit_FileName = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit_FileName.setEnabled(False)
        self.lineEdit_FileName.setGeometry(QtCore.QRect(70, 50, 321, 20))
        self.lineEdit_FileName.setObjectName("lineEdit_FileName")
        self.pushButton_Start = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_Start.setGeometry(QtCore.QRect(400, 20, 81, 51))
        self.pushButton_Start.setCheckable(False)
        self.pushButton_Start.setChecked(False)
        self.pushButton_Start.setAutoRepeat(False)
        self.pushButton_Start.setAutoExclusive(False)
        self.pushButton_Start.setFlat(False)
        self.pushButton_Start.setObjectName("pushButton_Start")
        self.progressBar = QtWidgets.QProgressBar(self.groupBox)
        self.progressBar.setGeometry(QtCore.QRect(70, 80, 321, 21))
        self.progressBar.setMaximum(100)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.progressBar.setFormat("")
        self.progressBar.setObjectName("progressBar")
        self.label_4 = QtWidgets.QLabel(self.groupBox)
        self.label_4.setGeometry(QtCore.QRect(10, 80, 31, 21))
        self.label_4.setObjectName("label_4")
        self.pushButton_Stop = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_Stop.setEnabled(False)
        self.pushButton_Stop.setGeometry(QtCore.QRect(400, 80, 81, 21))
        self.pushButton_Stop.setObjectName("pushButton_Stop")
        self.checkBox_Open = QtWidgets.QCheckBox(self.groupBox)
        self.checkBox_Open.setEnabled(False)
        self.checkBox_Open.setGeometry(QtCore.QRect(340, 20, 51, 21))
        self.checkBox_Open.setObjectName("checkBox_Open")
        self.comboBox_Schedule = QtWidgets.QComboBox(Dialog)
        self.comboBox_Schedule.setGeometry(QtCore.QRect(70, 10, 321, 21))
        self.comboBox_Schedule.setObjectName("comboBox_Schedule")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(4, 10, 60, 21))
        self.label.setObjectName("label")
        self.plainTextEditLogger = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEditLogger.setGeometry(QtCore.QRect(0, 160, 491, 271))
        self.plainTextEditLogger.setObjectName("plainTextEditLogger")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.comboBox_Schedule, self.timeEdit_StartTm)
        Dialog.setTabOrder(self.timeEdit_StartTm, self.timeEdit_EndTm)
        Dialog.setTabOrder(self.timeEdit_EndTm, self.checkBox_Open)
        Dialog.setTabOrder(self.checkBox_Open, self.lineEdit_FileName)
        Dialog.setTabOrder(self.lineEdit_FileName, self.pushButton_Start)
        Dialog.setTabOrder(self.pushButton_Start, self.pushButton_Stop)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "CoolFM Recoder (KBS Radio 89.1Mhz)"))
        self.groupBox.setTitle(_translate("Dialog", "녹화 설정"))
        self.timeEdit_StartTm.setDisplayFormat(_translate("Dialog", "HH:mm:ss"))
        self.label_2.setText(_translate("Dialog", "시작시각"))
        self.label_3.setText(_translate("Dialog", "파일이름"))
        self.timeEdit_EndTm.setDisplayFormat(_translate("Dialog", "HH:mm:ss"))
        self.label_5.setText(_translate("Dialog", "종료시각"))
        self.pushButton_Start.setText(_translate("Dialog", "시작"))
        self.label_4.setText(_translate("Dialog", "진행"))
        self.pushButton_Stop.setText(_translate("Dialog", "중지"))
        self.checkBox_Open.setText(_translate("Dialog", "보라"))
        self.label.setText(_translate("Dialog", "방송스케쥴"))

