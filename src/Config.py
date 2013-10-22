# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Config
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@bu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ui_config import Ui_Config

class Config(QDialog, Ui_Config):

    accepted = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, iface, location, img_pattern, stack_pattern):
        self.iface = iface
        QWidget.__init__(self)
        self.setupUi(self)
        ### Data
        self.location = location
        self.image_pattern = img_pattern
        self.stack_pattern = stack_pattern
        ### Finish setup
        self.setup_config()

    def setup_config(self):
        ### Setup location text field and open button
        self.edit_location.setText(self.location)
        self.button_location.clicked.connect(self.select_location)
        ### Setup stack directory & patterns
        self.edit_image.setText(self.image_pattern)
        self.edit_stack.setText(self.stack_pattern)
        ### Setup dialog buttons
        # Init buttons
        self.ok = self.button_box.button(QDialogButtonBox.Ok)
        self.cancel = self.button_box.button(QDialogButtonBox.Cancel)
        # Add signals
        self.ok.pressed.connect(self.accept_config)
        self.cancel.pressed.connect(self.cancel_config)

    def select_location(self):
        """
        Brings up a QFileDialog allowing user to select a folder
        """
        self.location = QFileDialog.getExistingDirectory(self, 
                            'Select stack location',
                            self.location,
                            QFileDialog.ShowDirsOnly)
        self.edit_location.setText(self.location) 

    def accept_config(self):
        print 'Okay pressed!'
        self.accepted.emit()

    def cancel_config(self):
        print 'Cancel pressed!'
        self.canceled.emit()
