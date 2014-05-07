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
from PyQt4 import QtCore
from PyQt4 import QtGui

from PyQt4.QtCore import * # TODO remove * imports
from PyQt4.QtGui import *

from ui_config import Ui_Config

from custom_form import CustomForm

class Config(QDialog, Ui_Config):

    accepted = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, iface, location, ts_data_models):
        self.iface = iface
        QWidget.__init__(self)
        self.setupUi(self)
        ### Data
        self.location = location
        self.ts_data_models = ts_data_models

        ### Setup required information
        self.data_model_str = [_ts.__str__ for _ts in self.ts_data_models]

        ### Finish setup
        self.setup_config()

    def setup_config(self):
        ### Data model types
        self.combox_ts_model.clear()
        self.combox_ts_model.addItems(self.data_model_str)

        self.combox_ts_model.activated.connect(self.ts_model_changed)

        ### Setup location text field and open button
        self.edit_location.setText(self.location)
        self.button_location.clicked.connect(self.select_location)

        ### Setup stacked widget for custom options
        self.stacked_widget = QtGui.QStackedWidget()
        
        for i, _ts in enumerate(self.ts_data_models):
            # Test for custom configurations

            has_custom_form = True

            if not hasattr(_ts, 'custom_options') or \
                not callable(getattr(_ts, 'set_custom_options', None)):    
                has_custom_form = False
            else:
                if not isinstance(_ts.custom_options, list):
                    print 'Custom options for timeseries improperly described'
                    has_custom_form = False
                if len(_ts.custom_options) == 0:
                    print 'Custom controls for timeseries improperly described'
                    has_custom_form = False
                    
                if not isinstance(_ts.custom_options[0], list):
                    print 'Custom controls for timeseries improperly described'
                    has_custom_form = False

            if has_custom_form is True:
                custom_form = CustomForm(_ts.custom_options)
            else:
                custom_form = QtGui.QLabel('No custom options')

            custom_form.setParent(self.stacked_widget)
            self.stacked_widget.insertWidget(i, custom_form)

        self.custom_layout = QtGui.QVBoxLayout()
        self.custom_layout.addWidget(self.stacked_widget)
        self.custom_widget.setLayout(self.custom_layout)

        ### Setup dialog buttons
        # Init buttons
        self.ok = self.button_box.button(QDialogButtonBox.Ok)
        self.cancel = self.button_box.button(QDialogButtonBox.Cancel)
        # Add signals
        self.ok.pressed.connect(self.accept_config)
        self.cancel.pressed.connect(self.cancel_config)

    @QtCore.pyqtSlot(int)
    def ts_model_changed(self, index):
        """ Fired when combo box is changed so stacked_widget can change """
        if index != self.stacked_widget.currentIndex():
            self.stacked_widget.setCurrentIndex(index)
            self.combox_ts_model.setCurrentIndex(index)

    @QtCore.pyqtSlot()
    def select_location(self):
        """
        Brings up a QFileDialog allowing user to select a folder
        """
        self.location = QFileDialog.getExistingDirectory(self, 
                            'Select stack location',
                            self.location,
                            QFileDialog.ShowDirsOnly)
        self.edit_location.setText(self.location) 

    @QtCore.pyqtSlot()
    def accept_config(self):
        print 'Okay pressed!'
        
        self.model_index = self.combox_ts_model.currentIndex()
        self.location = self.edit_location.text()

        self.accepted.emit()

    @QtCore.pyqtSlot()    
    def cancel_config(self):
        print 'Cancel pressed!'
        self.canceled.emit()

# main function for testing
if __name__ == "__main__":
    import os
    import sys
    app = QtGui.QApplication(sys.argv)

    from timeseries_ccdc import CCDCTimeSeries
    from timeseries_ccdc_v9LIVE import CCDCTimeSeries_v9LIVE

    widget = Config(app, os.getcwd(), [CCDCTimeSeries, CCDCTimeSeries_v9LIVE])

    widget.show()
    sys.exit(app.exec_())
