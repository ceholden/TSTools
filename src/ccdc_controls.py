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
from qgis.core import *

import numpy as np

import datetime as dt
import fnmatch
from itertools import izip
import os

from ui_ccdctools import Ui_CCDCTools as Ui_Widget


class CCDCControls(QWidget, Ui_Widget):
    
    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QWidget.__init__(self)
        self.setupUi(self)

    def update_options(self, ts, opt):
        print 'Ctrl updates...'
        ### Show/don't show clicks
        self.cbox_showclick.setChecked(opt['show_click'])

        ### Raster band select
        if self.combox_band.count() == 0:
            self.combox_band.addItems(ts.band_names)
        self.combox_band.setCurrentIndex(opt['band'])
        
        ### Ylim min and max
        # Auto scale
        self.cbox_scale.setChecked(opt['scale'])
        # Manual scale & auto-scale display
        self.edit_min.setText(str(opt['min'][opt['band']]))
        self.edit_max.setText(str(opt['max'][opt['band']]))
        
        ### Fmask, fit & breaks on/off
        self.cbox_fmask.setChecked(opt['fmask'])
        self.cbox_ccdcfit.setChecked(opt['fit'])
        self.cbox_ccdcbreak.setChecked(opt['break'])
        
        ### Click a point, add the layer
        self.cbox_plotlayer.setChecked(opt['plotlayer'])

    def update_table(self, ts, opt):
        print 'Table updates...'
        # Set header labels
        self.image_table.setHorizontalHeaderLabels(
            ['Add/Remove', 'Date', 'ID'])
        
        # Propagate table
        self.image_table.setRowCount(ts.length)
        for row, (date, img) in enumerate(izip(ts.dates, ts.image_ids)):
            cbox = QTableWidgetItem()
            cbox.setFlags(Qt.ItemIsUserCheckable |
                          Qt.ItemIsEnabled)
            cbox.setCheckState(Qt.Unchecked)
            cbox.setTextAlignment(Qt.AlignHCenter)
            self.image_table.setItem(row, 0, cbox)

            _date = QTableWidgetItem(date.strftime('%Y-%j'))
            _date.setFlags(Qt.ItemIsEnabled)
            _date.setTextAlignment(Qt.AlignHCenter)
            _date.setTextAlignment(Qt.AlignVCenter)
            self.image_table.setItem(row, 1, _date)

            _img = QTableWidgetItem(img)
            _img.setFlags(Qt.ItemIsEnabled)
            _img.setTextAlignment(Qt.AlignHCenter)
            _img.setTextAlignment(Qt.AlignVCenter)
            self.image_table.setItem(row, 2, _img)

        cbox = self.image_table.cellWidget(0, 0)

    def disconnect(self):
        # TODO
        pass
