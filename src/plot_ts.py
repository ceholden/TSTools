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

import os
import datetime as dt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas

import numpy as np

import settings as setting

# Note: FigureCanvas is also a QWidget
class TSPlot(FigureCanvas):

    def __str__(self):
        return "Time Series Plot"

    def __init__(self, parent=None):
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
        self.plot()

    def setup_plots(self):
        # matplotlib
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setAutoFillBackground(False)
        self.axes.set_ylim([0, 10000])
        self.fig.tight_layout()

    def update_plot(self, ts):
        """ Fetches new information and then calls to plot
        """

        print 'Updating plot...'

        self.px, self.py = ts.get_px(), ts.get_py()
        if self.px is not None and self.py is not None:
            # Add + 1 so we index on 1,1 instead of 0,0 (as in ENVI/MATLAB)
            self.px, self.py = self.px + 1, self.py + 1

        self.x = ts.dates
        self.y = ts.get_data(setting.plot['mask'])[setting.plot['band'], :]

        if setting.plot['fit'] is True and ts.result is not None:
            if len(ts.result) > 0:
                self.mx, self.my = ts.get_prediction(setting.plot['band'])
            else:
                self.mx, self.my = (np.zeros(0), np.zeros(0))
        if setting.plot['break'] is True and ts.result is not None:
            if len(ts.result) > 1:
                self.bx, self.by = ts.get_breaks(setting.plot['band'])
            else:
                self.bx, self.by = (np.zeros(0), np.zeros(0))
        self.plot(ts)

    def plot(self, ts=None):
        """ Matplotlib plot of time series
        """
        self.axes.clear()

        title = 'Time series - row: %s col: %s' % (
            str(self.py), str(self.px))
        self.axes.set_title(title)

        self.axes.set_xlabel('Date')
        if ts is None:
            self.axes.set_ylabel('Band')
        else:
            self.axes.set_ylabel(ts.band_names[setting.plot['band']])

        self.axes.grid(True)

        self.axes.set_ylim([setting.plot['min'][setting.plot['band']],
                            setting.plot['max'][setting.plot['band']]])

        if setting.plot['xmin'] is not None \
                and setting.plot['xmax'] is not None:
            self.axes.set_xlim([dt.date(setting.plot['xmin'], 01, 01),
                                dt.date(setting.plot['xmax'], 12, 31)])

        # Plot time series data
        line, = self.axes.plot(self.x, self.y,
                       marker='o', ls='', color='k',
                       picker=setting.plot['picker_tol'])

        # Plot modeled fit
        if setting.plot['fit'] is True:
            for i in xrange(len(self.mx)):
                self.axes.plot(self.mx[i], self.my[i], linewidth=2)

        # Plot break points
        if setting.plot['break'] is True:
            for i in xrange(len(self.bx)):
                self.axes.plot(self.bx[i], self.by[i], 'ro',
                    mec='r', mfc='none', ms=10, mew=5)

        # Redraw
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def save_plot(self):
        """ Save the matplotlib figure
        """
        ### Parse options from settings
        fname = setting.save_plot['fname']
        fformat = setting.save_plot['format']
        facecolor = setting.save_plot['facecolor']
        edgecolor = setting.save_plot['edgecolor']
        transparent = setting.save_plot['transparent']

        # Get real path to filename
        fname = os.path.realpath(fname)

        # Format the output path
        directory = os.path.dirname(fname)

        # Check for file extension
        if fname.split('.')[-1].lower() != fformat:
            fname = fname + '.' + fformat

        self.fig.savefig(fname, format=fformat,
                         facecolor=facecolor, edgecolor=edgecolor,
                         transparent=transparent)

        return True

    def disconnect(self):
        pass
