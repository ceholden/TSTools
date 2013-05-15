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
        dopts['picker_tol'] = 2

        ### Setup datasets
        # Actual data
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        # Modeled fitted data
        self.mx = np.zeros(0)
        self.my = np.zeros(0)
        # Breaks
        self.bx = np.zeros(0)
        self.by = np.zeros(0)
        # Location of pixel plotted
        self.px = None
        self.py = None

        # Setup plots
        self.setup_plots()
        self.plot(dopts)

    def setup_plots(self):
        # matplotlib
        self.fig = Figure()
#        self.fig.set_facecolor('white')
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setAutoFillBackground(False)
        self.axes.set_ylim([0, 10000])

            
    def update_plot(self, ts, opt):
        """
        Fetches new information and then calls to plot
        """
        
        print 'Updating plot...'
        
        self.px, self.py = ts.x + 1, ts.y + 1
        self.x = ts.dates
        self.y = ts.data[opt['band'], :]

        if opt['fit'] is True and ts.reccg is not None:
            if len(ts.reccg) > 0:
                self.mx, self.my = ts.get_prediction(opt['band'])
            else:
                self.mx, self.my = (np.zeros(0), np.zeros(0))
        if opt['break'] is True and ts.reccg is not None:
            if len(ts.reccg) > 1:
                self.bx, self.by = ts.get_breaks(opt['band'])
            else:
                self.bx, self.by = (np.zeros(0), np.zeros(0))
        self.plot(opt)

        print hex(id(ts))

    def plot(self, options=None):
        """
        Matplotlib plot of time series
        """
        print 'Plotting...'
        self.axes.clear()

        title = 'Time series - row: %s col: %s' % (
            str(self.py), str(self.px))
        self.axes.set_title(title)
        self.axes.set_xlabel('Date')
        self.axes.set_ylabel('Band %s (SR x 10000)' % str(options['band']))
        self.axes.grid(True)

        if options:
            self.axes.set_ylim([options['min'][options['band']], 
                                options['max'][options['band']]])
        # Plot time series data
        line, = self.axes.plot(self.x, self.y, 
                       marker='o', ls='', color='k',
                       picker=options['picker_tol'])
        # Plot modeled fit
        if options and options['fit'] == True:
            for i in xrange(len(self.mx)):
                self.axes.plot(self.mx[i], self.my[i], linewidth=2)
        # Plot break points
        if options and options['break'] == True:
            for i in xrange(len(self.bx)):
                self.axes.plot(self.bx[i], self.by[i], 'ro',
                    mec='r', mfc='none', ms=10, mew=5)
        # Redraw
        self.fig.canvas.draw()


    def disconnect(self):
        pass
