# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCToolsDialog
                                 A QGIS plugin
 Plotting & visualization tools for CCDC Landsat time series analysis
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

from ui_plotsave import Ui_PlotSave

import os

from matplotlib.colors import ColorConverter

import ccdc_settings as setting

class SavePlotDialog(QDialog, Ui_PlotSave):
    
    # Signals
    save_plot_requested = pyqtSignal()
    save_plot_closed = pyqtSignal()

    def __init__(self, iface):
        # Standard UI setup
        self.iface = iface
        QWidget.__init__(self)
        self.setupUi(self)

        # Setup path for output of plot
        setting.save_plot['fname'] = os.path.join(os.getcwd(), 
                                          setting.save_plot['fname'])
        # Finish UI setup
        self.setup_save_dialog()

    def setup_save_dialog(self):
        """ Finishes UI setup by configuring UI elements and adding signals
        """
        # Setup line edit for save location
        self.edit_plot_fname.setText(setting.save_plot['fname'])
        # Add slot for open dialog
        self.edit_plot_fname.editingFinished.connect(self.set_save_location)
        self.but_plot_fname.clicked.connect(self.find_save_location)
        
        # Plot format
        self.combox_plot_format.setCurrentIndex(
            self.combox_plot_format.findText(setting.save_plot['format']))
        self.combox_plot_format.currentIndexChanged.connect(self.set_format)

        # Facecolor/edgecolor
        self.edit_facecolor.setText(setting.save_plot['facecolor'])
        self.edit_edgecolor.setText(setting.save_plot['edgecolor'])
        self.edit_facecolor.editingFinished.connect(self.set_facecolor)
        self.edit_edgecolor.editingFinished.connect(self.set_edgecolor)

        # Transparent
        self.cbox_transparent.setChecked(setting.save_plot['transparent'])
        self.cbox_transparent.stateChanged.connect(self.set_transparent)

        # Cancel/OK
        self.save = self.bbox_choice.button(QDialogButtonBox.Save)
        self.cancel = self.bbox_choice.button(QDialogButtonBox.Cancel)
        self.help = self.bbox_choice.button(QDialogButtonBox.Help)
        self.save.pressed.connect(self.save_plot_request)
        self.cancel.pressed.connect(self.cancel_plot_request)
        self.help.pressed.connect(self.help_plot_request)


    def find_save_location(self):
        """ Signal slot for finding plot save filename
        """
        # Open dialog for save file
        setting.save_plot['fname'] = str(QFileDialog.getSaveFileName(self,
                            'Select save location',
                            setting.save_plot['fname']))
        self.edit_plot_fname.setText(setting.save_plot['fname'])

    def set_save_location(self):
        """ Signal slot for editingFinished to grab new save location
        """
        setting.save_plot['fname'] = str(self.edit_plot_fname.text())

    def set_format(self, index):
        """ Signal slot for plot format combobox
        """
        setting.save_plot['format'] = str(self.combox_plot_format.
                                          itemText(index))

    def set_facecolor(self):
        """ Signal slot for setting of facecolor
        """
        color = str(self.edit_facecolor.text())

        if self.validate_color(color):
            setting.save_plot['facecolor'] = color
        else:
            print 'Error: no such color. Restoring previous choice'
            self.edit_facecolor.setText(setting.save_plot['facecolor'])

    def set_edgecolor(self):
        """ Signal slot for setting of edgecolor
        """
        color = str(self.edit_edgecolor.text())

        if self.validate_color(str(color)) == True:
            setting.save_plot['edgecolor'] = color
        else:
            print 'Error: no such color. Restoring previous choice'
            self.edit_edgecolor.setText(setting.save_plot['edgecolor']) 

    def set_transparent(self, state):
        """ Signal slot for setting transparency to True/False
        """
        if state == Qt.Checked:
            setting.save_plot['transparent'] = True
        elif state == Qt.Unchecked:
            setting.save_plot['transparent'] = False

    def save_plot_request(self):
        """ Signal slot for a saving the plot
        """
        self.save_plot_requested.emit()
        self.save_plot_closed.emit()

    def cancel_plot_request(self):
        """ Signal slot for canceling the plot save request
        """
        self.save_plot_closed.emit()

    def help_plot_request(self):
        """ Signal slot for help button
        """
        print 'Who needs help?!' #TODO

    def validate_color(self, color):
        """ Function for validating Matplotlib user input color choice
        """
        print color
        c = ColorConverter()
        try:
            print c.to_rgb(color)
        except:
            return False
        return True
