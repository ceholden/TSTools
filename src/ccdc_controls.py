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

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint

import numpy as np

import datetime as dt
import fnmatch
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
        ### Raster band select
        print 'Len combox_band %s' % str(self.combox_band.count())
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

    def update_table(self, ts, opt):
        print 'Table updates...'


    def disconnect(self):
        # TODO
        pass
