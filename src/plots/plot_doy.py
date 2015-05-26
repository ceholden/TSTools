# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Within-year timeseries plot (years represented using colors)
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@gmail.com
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
import matplotlib as mpl
import mpl_toolkits.axes_grid1 as mpl_grid

import numpy as np

from . import base_plot
from tstools.ts_driver.ts_manager import tsm
from tstools import settings


class DOYPlot(base_plot.BasePlot):

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

    def update_plot(self):
        """ Fetches new information and then calls plot
        """
        self.px, self.py = tsm.ts.get_px(), tsm.ts.get_py()
        if self.px is not None and self.py is not None:
            # Add + 1 so we index on 1,1 instead of 0,0 (as in ENVI/MATLAB)
            self.px, self.py = self.px + 1, self.py + 1

        self.x = np.array([int(d.strftime('%j')) for d in tsm.ts.dates])
        self.year = np.array([d.year for d in tsm.ts.dates])
        self.y = tsm.ts.get_data(settings.plot['mask'])[settings.plot['band'], :]

        if settings.plot['fit'] is True and tsm.ts.result is not None:
            if len(tsm.ts.result) > 0:
                self.mx, self.my = tsm.ts.get_prediction(settings.plot['band'])
            else:
                self.mx, self.my = (np.zeros(0), np.zeros(0))

            self.mx_year = []
            for _mx in self.mx:
                self.mx_year.append(np.array([d.year for d in _mx]))

        if settings.plot['break'] is True and tsm.ts.result is not None:
            if len(tsm.ts.result) > 1:
                self.bx, self.by = tsm.ts.get_breaks(settings.plot['band'])
            else:
                self.bx, self.by = (np.zeros(0), np.zeros(0))
        self.plot()

    def plot(self):
        """ Matplotlib plot of time series stacked by DOY
        """
        self.axes.clear()

        title = 'Time series - row: {r} col: {c}'.format(
            r=str(self.py), c=str(self.px))
        self.axes.set_title(title)

        self.axes.set_xlabel('Day of Year')
        if tsm.ts is None:
            self.axes.set_ylabel('Band')
        else:
            self.axes.set_ylabel(tsm.ts.band_names[settings.plot['band']])

        self.axes.grid(True)
        self.axes.set_ylim([settings.plot['min'][settings.plot['band']],
                            settings.plot['max'][settings.plot['band']]])
        self.axes.set_xlim(0, 366)

        if settings.plot['xmin'] is not None \
                and settings.plot['xmax'] is not None:
            # Find array indexes for year range
            self.yr_range = np.arange(
                np.where(self.year >= settings.plot['xmin'])[0][0],
                np.where(self.year <= settings.plot['xmax'])[0][-1])
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
                               picker=settings.plot['picker_tol'])

        # Only put colorbar if we have data
        if tsm.ts is not None:
            # Setup layout to add space
            # http://matplotlib.org/mpl_toolkits/axes_grid/users/overview.html#axesdivider
            divider = mpl_grid.make_axes_locatable(self.axes)
            cax = divider.append_axes('right', size='5%', pad=0.05)
            # Reset colorbar so it doesn't overwrite itself...
            if self.cbar is not None:
                self.fig.delaxes(self.fig.axes[1])
                self.fig.subplots_adjust(right=0.90)
            self.cbar = self.fig.colorbar(sp, cax=cax)

        if settings.plot['fit'] is True:
            med_year = []
            fit_plt = []
            # Find median year and plot that result
            for n, _yr in enumerate(self.mx_year):
                # Make sure _yr is not empty array
                if len(_yr) == 0:
                    continue
                # Determine median year
                med = int(np.median(_yr))
                # Make sure median year is in our current x-axis
                if settings.plot['xmin'] > med or settings.plot['xmax'] < med:
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

    def disconnect(self):
        pass
