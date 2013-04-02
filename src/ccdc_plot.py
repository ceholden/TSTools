# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCTools
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
from qgis.utils import iface

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas

import datetime as dt

import numpy as np

# Note: FigureCanvas is also a QWidget
class CCDCPlot(FigureCanvas):
    
    def __init__(self, parent=None):
        # Setup some defaults
        dopts = {}
        dopts['band'] = 0
        dopts['min'] = np.zeros(1, dtype=np.int)
        dopts['max'] = np.ones(1, dtype=np.int) * 10000
        dopts['fit'] = True
        dopts['break'] = True
        # Setup datasets
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        self.reccg = None

        # Setup plots
        self.setup_plots()
        self.plot(dopts)

    def setup_plots(self):
        layout = QHBoxLayout()
        # matplotlib
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setAutoFillBackground(False)
        self.axes.set_ylim([0, 10000])

        # TODO: move these into the plot command...?
#        self.axes.set_title('Time Series')
#        self.axes.set_xlabel('Date')
#        self.axes.set_ylabel('SR x 10000')
    
    def update_plot(self, ts, opt):
        print 'Updating plot...'
        self.x = ts.dates
        self.y = ts.data[opt['band'], :]
        print 'update opt band %s' % str(opt['band'])
        self.reccg = ts.reccg
        self.plot(opt)

    def plot(self, options=None):
        print 'Plotting...'
        self.axes.clear()
        if options:
            self.axes.set_ylim([options['min'][options['band']], 
                                options['max'][options['band']]])
        # Plot time series data
        self.axes.plot(self.x, self.y, 
                       marker='o', ls='', color='k')
        # Plot modeled fit
        if options['fit'] == True and self.reccg != None:
            if len(self.reccg) > 0:
                for rec in self.reccg:
                    if options['band'] >= rec['coefs'].shape[1]:
                        break
                    # Create sequence of MATLAB ordinal dates
                    mx = np.linspace(rec['t_start'],
                                     rec['t_end'],
                                     rec['t_end'] - rec['t_start'])
                    coef = rec['coefs'][:, options['band']]
                    # Calculate model predictions
                    my = (coef[0] + 
                          coef[1] * mx +
                          coef[2] * np.cos(2 * np.pi / 365 * mx) + 
                          coef[3] * np.sin(2 * np.pi / 365 * mx))
                    # Transform MATLAB oridnal date into Python datetime
                    mx = [dt.datetime.fromordinal(int(m)) -
                                                  dt.timedelta(days = 366)
                                                  for m in mx]
                    self.axes.plot(mx, my, linewidth=2)
        # Plot break points
        if options['break'] == True and self.reccg != None:
            if len(self.reccg) > 1:
                for rec in self.reccg[0:-1]:
                    mx = (dt.datetime.fromordinal(int(rec['t_break'])) -
                                                 dt.timedelta(days = 366))
                    print 'Break:'
                    print mx
                    index = [i for i, date in 
                             enumerate(self.x) if date == mx][0]
                    print 'Index:'
                    print index
                    if index < len(self.y) and index >= 0:
                        my = self.y[index]
                        print 'Y break:'
                        print my
                        self.axes.plot(mx, my, 'ro', mec='r', 
                                       mfc='none', ms=10, mew=5)
        self.fig.canvas.draw()


    def disconnect(self):
        pass
