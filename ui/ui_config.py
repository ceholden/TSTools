# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/ui_config.ui'
#
# Created: Mon Apr  8 17:56:35 2013
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Config(object):
    def setupUi(self, Config):
        Config.setObjectName(_fromUtf8("Config"))
        Config.resize(357, 240)
        self.gridLayout = QtGui.QGridLayout(Config)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.edit_location = QtGui.QLineEdit(Config)
        self.edit_location.setObjectName(_fromUtf8("edit_location"))
        self.gridLayout.addWidget(self.edit_location, 2, 0, 1, 1)
        self.button_location = QtGui.QPushButton(Config)
        self.button_location.setObjectName(_fromUtf8("button_location"))
        self.gridLayout.addWidget(self.button_location, 2, 1, 1, 1)
        self.lab_config = QtGui.QLabel(Config)
        self.lab_config.setAlignment(QtCore.Qt.AlignCenter)
        self.lab_config.setObjectName(_fromUtf8("lab_config"))
        self.gridLayout.addWidget(self.lab_config, 0, 0, 1, 2)
        self.label = QtGui.QLabel(Config)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(Config)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 5, 0, 1, 1)
        self.lineEdit = QtGui.QLineEdit(Config)
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.gridLayout.addWidget(self.lineEdit, 4, 0, 1, 2)
        self.lineEdit_2 = QtGui.QLineEdit(Config)
        self.lineEdit_2.setObjectName(_fromUtf8("lineEdit_2"))
        self.gridLayout.addWidget(self.lineEdit_2, 6, 0, 1, 2)
        self.lab_location = QtGui.QLabel(Config)
        self.lab_location.setObjectName(_fromUtf8("lab_location"))
        self.gridLayout.addWidget(self.lab_location, 1, 0, 1, 2)
        self.buttonBox = QtGui.QDialogButtonBox(Config)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 7, 1, 1, 1)

        self.retranslateUi(Config)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Config.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Config.reject)
        QtCore.QMetaObject.connectSlotsByName(Config)

    def retranslateUi(self, Config):
        Config.setWindowTitle(QtGui.QApplication.translate("Config", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.button_location.setText(QtGui.QApplication.translate("Config", "Open", None, QtGui.QApplication.UnicodeUTF8))
        self.lab_config.setText(QtGui.QApplication.translate("Config", "Configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Config", "Stack directory pattern:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Config", "Stack pattern:", None, QtGui.QApplication.UnicodeUTF8))
        self.lineEdit.setText(QtGui.QApplication.translate("Config", "LND*", None, QtGui.QApplication.UnicodeUTF8))
        self.lineEdit_2.setText(QtGui.QApplication.translate("Config", "*stack", None, QtGui.QApplication.UnicodeUTF8))
        self.lab_location.setText(QtGui.QApplication.translate("Config", "Stacked time series location:", None, QtGui.QApplication.UnicodeUTF8))

