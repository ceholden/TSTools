# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/ui_ccdctools.ui'
#
# Created: Thu Mar 28 21:03:59 2013
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_CCDCTools(object):
    def setupUi(self, CCDCTools):
        CCDCTools.setObjectName(_fromUtf8("CCDCTools"))
        CCDCTools.resize(640, 480)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(CCDCTools.sizePolicy().hasHeightForWidth())
        CCDCTools.setSizePolicy(sizePolicy)
        CCDCTools.setMinimumSize(QtCore.QSize(640, 480))
        self.widget = QtGui.QWidget(CCDCTools)
        self.widget.setGeometry(QtCore.QRect(0, 0, 640, 60))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.cbox_active = QtGui.QCheckBox(self.widget)
        self.cbox_active.setObjectName(_fromUtf8("cbox_active"))
        self.horizontalLayout.addWidget(self.cbox_active)
        self.cbox_tool = QtGui.QCheckBox(self.widget)
        self.cbox_tool.setObjectName(_fromUtf8("cbox_tool"))
        self.horizontalLayout.addWidget(self.cbox_tool)
        self.cbox_fmask = QtGui.QCheckBox(self.widget)
        self.cbox_fmask.setObjectName(_fromUtf8("cbox_fmask"))
        self.horizontalLayout.addWidget(self.cbox_fmask)
        self.widget_2 = QtGui.QWidget(CCDCTools)
        self.widget_2.setGeometry(QtCore.QRect(0, 60, 640, 60))
        self.widget_2.setObjectName(_fromUtf8("widget_2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setMargin(0)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label = QtGui.QLabel(self.widget_2)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_2.addWidget(self.label)
        self.combox_band_select = QtGui.QComboBox(self.widget_2)
        self.combox_band_select.setObjectName(_fromUtf8("combox_band_select"))
        self.horizontalLayout_2.addWidget(self.combox_band_select)
        self.stackedWidget = QtGui.QStackedWidget(CCDCTools)
        self.stackedWidget.setGeometry(QtCore.QRect(0, 120, 640, 360))
        self.stackedWidget.setObjectName(_fromUtf8("stackedWidget"))

        self.retranslateUi(CCDCTools)
        QtCore.QMetaObject.connectSlotsByName(CCDCTools)

    def retranslateUi(self, CCDCTools):
        CCDCTools.setWindowTitle(QtGui.QApplication.translate("CCDCTools", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.cbox_active.setText(QtGui.QApplication.translate("CCDCTools", "Plot", None, QtGui.QApplication.UnicodeUTF8))
        self.cbox_tool.setText(QtGui.QApplication.translate("CCDCTools", "Select tool", None, QtGui.QApplication.UnicodeUTF8))
        self.cbox_fmask.setText(QtGui.QApplication.translate("CCDCTools", "Fmask?", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("CCDCTools", "Raster Band", None, QtGui.QApplication.UnicodeUTF8))

