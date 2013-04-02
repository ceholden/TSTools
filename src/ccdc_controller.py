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
        self.opt['min'] = 0
        self.opt['max'] = 10000
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
            self.update_display()

    def update_display(self):
        """
        Once ts is read, update controls & plot with relevant information
        (i.e. update)
        """
        self.ctrl.update_controls(self.ts, self.opt)
        self.plt.update_plot(self.ts, self.opt)

    def add_signals(self):
        # Raster band select checkbox
#        QObject.connect(self.ctrl.combox_band,
#                    SIGNAL('currentIndexChanged(int)'), self.set_band_select)
        self.ctrl.combox_band.currentIndexChanged.connect(partial(
            self.set_band_select))
        
        # Plot Y min & max
        validator = QIntValidator(0, 10000, self.ctrl)
        #self.ctrl.edit_min.setValidator(validator)
        self.ctrl.edit_min.returnPressed.connect(partial(
            self.set_min, self.ctrl.edit_min, validator))
        # Plot Y max
        # self.ctrl.edit_max.setValidator(validator)
        self.ctrl.edit_max.returnPressed.connect(partial(
            self.set_max, self.ctrl.edit_max, validator))

        # End date #TODO
        # Show or hide Fmask checkbox
#        QObject.connect(self.ctrl.cbox_fmask,
#                    SIGNAL('currentIndexChanged(int)'), self.set_fmask)
        self.ctrl.cbox_fmask.stateChanged.connect(self.set_fmask)


    ### Slots

    def set_band_select(self, index):
        self.opt['band'] = index
        self.plt.update_plot(self.ts, self.opt)

    def set_min(self, edit, validator):
        state, pos = validator.validate(edit.text(), 0)

        if state == QValidator.Acceptable:
            self.opt['min'] = int(edit.text())
        self.plt.update_plot(self.ts, self.opt)
    
    def set_max(self, edit, validator):
        state, pos = validator.validate(edit.text(), 0)

        if state == QValidator.Acceptable:
            self.opt['max'] = int(edit.text())
        self.plt.update_plot(self.ts, self.opt)

    def set_fmask(self, state):
        if (state == Qt.Checked):
            self.opt['fmask'] = True
        elif (state == Qt.Unchecked):
            self.opt['fmask'] = False
        # Update the data for without the masks
        self.ts.get_ts_pixel(self.ts.x, self.ts.y, self.opt['fmask'])
        self.plt.update_plot(self.ts, self.opt)

#    def plot_request(self, pos, button=None):
#        print 'Trying to plot...'
#        self.fetch_data(pos)

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
