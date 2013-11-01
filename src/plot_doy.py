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

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
import mpl_toolkits.axes_grid1 as mpl_grid

import numpy as np

import settings as setting

# Note: FigureCanvas is also a QWidget
class DOYPlot(FigureCanvas):

    def __str__(self):
        return "Stacked Day of Year Plot"

    def __init__(self, parent=None):
        ### Setup datasets
        # Actual data
        self.x = np.zeros(0)
        self.year = np.zeros(0)
        self.y = np.zeros(0)
        # Modeled fitted data
        self.mx = np.zeros(0)
        self.mx_year = np.zeros(0)
        self.my = np.zeros(0)
        # Location of pixel plotted
        self.px = None
        self.py = None
    
        # Store colorbar so we know to delete
        self.cbar = None
        # Store range of data
        self.yr_range = (0, 1)
        
        # Setup plots
        self.setup_plots()
        self.plot()

    def setup_plots(self):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setAutoFillBackground(False)
        self.axes.set_ylim([0, 10000])
        self.fig.tight_layout()

    def update_plot(self, ts):
        """ Fetches new information and then calls plot
        """
        self.px, self.py = ts.x + 1, ts.y + 1
        self.x = np.array([int(d.strftime('%j')) for d in ts.dates])
        self.year = np.array([d.year for d in ts.dates])
        self.y = ts.data[setting.plot['band'], :]
        
        if setting.plot['fit'] is True and ts.reccg is not None:
            if len(ts.reccg) > 0:
                self.mx, self.my = ts.get_prediction(setting.plot['band'])
            else:
                self.mx, self.my = (np.zeros(0), np.zeros(0))
            
            self.mx_year = []
            for _mx in self.mx:
                self.mx_year.append(np.array([d.year for d in _mx]))

        if setting.plot['break'] is True and ts.reccg is not None:
            if len(ts.reccg) > 1:
                self.bx, self.by = ts.get_breaks(setting.plot['band'])
            else:
                self.bx, self.by = (np.zeros(0), np.zeros(0))
        self.plot(ts)

    def plot(self, ts=None):
        """ Matplotlib plot of time series stacked by DOY
        """
        self.axes.clear()

        title = 'Time series - row: {r} col: {c}'.format(
            r=str(self.py), c=str(self.px))
        self.axes.set_title(title)

        self.axes.set_xlabel('Day of Year')
        if ts is None:
            self.axes.set_ylabel('Band')
        else:
            self.axes.set_ylabel(ts.band_names[setting.plot['band']])
        
        self.axes.grid(True)
        self.axes.set_ylim([setting.plot['min'][setting.plot['band']],
                            setting.plot['max'][setting.plot['band']]])
        self.axes.set_xlim(0, 366)


        if setting.plot['xmin'] is not None \
                and setting.plot['xmax'] is not None:
            self.yr_range = np.arange(
                np.where(self.year == setting.plot['xmin'])[0][0],
                np.where(self.year == setting.plot['xmax'])[0][-1])
        else:
            self.yr_range = np.arange(0, self.year.shape[0])

        # Specify the year min and max
        yr_min = 0
        yr_max = 1
        if len(self.year) > 0:
            yr_min = self.year.min()
            yr_max = self.year.max()
        
        # Setup colormap and mapper
        cmap = mpl.cm.get_cmap('jet')
        norm = mpl.colors.Normalize(vmin=yr_min, vmax=yr_max) 
        mapper = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)

        # Plot
        sp = self.axes.scatter(self.x[self.yr_range], self.y[self.yr_range],
                               cmap=cmap, c=self.year[self.yr_range],
                               norm=norm,
                               marker='o', edgecolors='none', s=25,
                               picker=setting.plot['picker_tol'])

        # Only put colorbar if we have data
        if ts is not None:
            # Setup layout to add space
            # http://matplotlib.org/mpl_toolkits/axes_grid/users/overview.html#axesdivider
            divider = mpl_grid.make_axes_locatable(self.axes)
            cax = divider.append_axes('right', size='5%', pad=0.05)
            # Reset colorbar so it doesn't overwrite itself...
            if self.cbar is not None:
                self.fig.delaxes(self.fig.axes[1])
                self.fig.subplots_adjust(right=0.90)
            self.cbar = self.fig.colorbar(sp, cax=cax)

        if setting.plot['fit'] is True:
            med_year = []
            fit_plt = []
            # Find median year and plot that result
            for n, _yr in enumerate(self.mx_year):
                # Determine median year
                med = int(np.median(_yr))
                # Make sure median year is in our current x-axis
                if setting.plot['xmin'] > med or setting.plot['xmax'] < med:
                    continue
                med_year.append(med)

                # Determine line color
                col = mapper.to_rgba(med)

                # Get index from mx predicted data for median year
                fit_range = np.arange(
                    np.where(_yr == med)[0][0],
                    np.where(_yr == med)[0][-1])

                # Recreate as DOY
                mx_doy = np.array([int(d.strftime('%j')) for d in
                                   self.mx[n][fit_range]])

                # Plot
                seg, = self.axes.plot(mx_doy, self.my[n][fit_range],
                                      color=col, linewidth=2)
                fit_plt.append(seg)

            if len(med_year) > 0:
                self.axes.legend(fit_plt,
                             ['Fit {n}: {y}'.format(n=n + 1, y=y)
                              for n, y in enumerate(med_year)])
        
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
        ### Format the output path
        directory = os.path.split(fname)[0]
        # Check for file extension
        if '.' not in os.path.split(fname)[1]:
            filename = '{f}.{e}'.format(f=os.path.split(fname)[1], e=fformat)
        # Add in directory if none
        if directory == '':
            directory = '.'
        # If directory does not exist, return False
        if not os.path.exists(directory):
            return False
        # Join and save
        filename = os.path.join(directory, filename)

        self.fig.savefig(filename, format=fformat,
                         facecolor=facecolor, edgecolor=edgecolor,
                         transparent=transparent)

        return True

    def disconnect(self):
        pass
