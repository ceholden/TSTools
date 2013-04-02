# -*- coding: utf-8 -*
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

from functools import partial

import numpy as np

from ccdc_timeseries import CCDCTimeSeries

class Controller(object):

    def __init__(self, control, plot):
        """
        Controller stores options specified in control panel & makes them
        available for plotter by handling all signals...
        """
        self.ctrl = control
        self.plt = plot
        
        ### Options
        self.opt = {}
        self.opt['plot'] = False
        self.opt['band'] = 0
        # TODO: turn these into specifics for each band
        self.opt['scale'] = True
        self.opt['scale_factor'] = 0.1
        self.opt['min'] = np.zeros(1, dtype=np.int)
        self.opt['max'] = np.ones(1, dtype=np.int) * 10000
        self.opt['fmask'] = True
        self.opt['fit'] = True
        self.opt['break'] = True
        
        self.add_signals() #TODO
        
    def get_time_series(self, location, image_pattern, stack_pattern):
        """
        Loads the time series class when called by ccdctools and feeds
        information to controls & plotter
        """
        self.ts = CCDCTimeSeries(location, image_pattern, stack_pattern)
        if self.ts:
            # Update plot & controls
            self.update_display()
            # Update band min/max
            # self.opt['min'] = np.zeros(self.ts.n_band, dtype=np.int)
            # self.opt['max'] = np.ones(self.ts.n_band, dtype=np.int) * 10000

    def update_display(self):
        """
        Once ts is read, update controls & plot with relevant information
        (i.e. update)
        """
        if self.opt['scale']:
            self.calculate_scale()
        self.ctrl.update_controls(self.ts, self.opt)
        self.plt.update_plot(self.ts, self.opt)

    def add_signals(self):
        """
        Add the signals to the options tab
        """
        ### Raster band select checkbox
        self.ctrl.combox_band.currentIndexChanged.connect(partial(
            self.set_band_select))
        
        ### Plot Y min & max
        # Auto scale
        self.ctrl.cbox_scale.stateChanged.connect(self.set_scale)
        # Manual set of min/max
        validator = QIntValidator(0, 10000, self.ctrl)
        #self.ctrl.edit_min.setValidator(validator)
        self.ctrl.edit_min.returnPressed.connect(partial(
            self.set_min, self.ctrl.edit_min, validator))
        # Plot Y max
        # self.ctrl.edit_max.setValidator(validator)
        self.ctrl.edit_max.returnPressed.connect(partial(
            self.set_max, self.ctrl.edit_max, validator))

        # Show or hide Fmask checkbox
        self.ctrl.cbox_fmask.stateChanged.connect(self.set_fmask)

    def calculate_scale(self):
        """
        Automatically calculate the min/max for time series plotting
        """
        self.opt['min'] = [np.min(b) * (1 - self.opt['scale_factor']) 
                           for b in self.ts.data[:, ]]
        self.opt['max'] = [np.max(b) * (1 + self.opt['scale_factor'])
                           for b in self.ts.data[:, ]]

    ### Slots
    def set_band_select(self, index):
        """
        Update the band selected & replot
        """
        self.opt['band'] = index
        self.ctrl.update_controls(self.ts, self.opt)
        self.plt.update_plot(self.ts, self.opt)

    def set_scale(self, state):
        """
        Automatically set the scale for each band & disable manual set
        """
        if (state == Qt.Checked):
            self.opt['scale'] = True
        elif (state == Qt.Unchecked):
            self.opt['scale'] = False
        self.ctrl.edit_min.setEnabled(not self.opt['scale'])
        self.ctrl.edit_max.setEnabled(not self.opt['scale'])

    def set_min(self, edit, validator):
        """
        If valid, update the minimum scale & replot
        """
        state, pos = validator.validate(edit.text(), 0)

        if state == QValidator.Acceptable:
            self.opt['min'] = int(edit.text())
        self.plt.update_plot(self.ts, self.opt)
    
    def set_max(self, edit, validator):
        """
        If valid, update the maximum scale & replot
        """
        state, pos = validator.validate(edit.text(), 0)

        if state == QValidator.Acceptable:
            self.opt['max'] = int(edit.text())
        self.plt.update_plot(self.ts, self.opt)

    def set_fmask(self, state):
        """
        Turn on or off the Fmask masking & replot
        """
        if (state == Qt.Checked):
            self.opt['fmask'] = True
        elif (state == Qt.Unchecked):
            self.opt['fmask'] = False
        # Update the data for without the masks
        self.ts.get_ts_pixel(self.ts.x, self.ts.y, self.opt['fmask'])
        self.plt.update_plot(self.ts, self.opt)

    def fetch_data(self, pos):
        print 'Pos: %s' % str(pos)
        px = int((pos[0] - self.ts.geo_transform[0]) / 
                 self.ts.geo_transform[1])
        py = int((pos[1] - self.ts.geo_transform[3]) / 
                 self.ts.geo_transform[5])
        self.ts.get_ts_pixel(px, py,
                             mask=self.opt['fmask'])
        self.ts.get_reccg_pixel(px, py)
        print 'Pixel x/y %s/%s' % (px, py)
        print 'nBreaks = %s' % len(self.ts.reccg)
        self.plt.update_plot(self.ts, self.opt)
