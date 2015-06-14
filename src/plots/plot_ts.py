# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Across year timeseries plot
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
import datetime as dt
import logging

import numpy as np

from . import base_plot
from .. import settings
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


class TSPlot(base_plot.BasePlot):

    def __str__(self):
        return "Timeseries Plot"

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
        self.title = ''

        # Setup plots
        self.setup_plots()
        self.plot()

    def _plot_series(self, axis, idx, series, band):
        """ Plot a timeseries from a timeseries ts_driver

        Args:
          axis (mpl.axes.Axes): axis to plot
          idx (int): index of all available plotting bands
          series (int): index of series within timeseries driver
          band (int): index of band within series within timeseries driver

        """
        x, y = tsm.ts.get_data(series, band, settings.plot['mask'])

        # Iterate over symbology descriptions
        for index, marker, color in zip(settings.plot_symbol[idx]['indices'],
                                        settings.plot_symbol[idx]['markers'],
                                        settings.plot_symbol[idx]['colors']):
            # Any points falling into this category?
            if index.size > 0:
                color = [c / 255.0 for c in color]
                axis.plot(x, y,
                          marker=marker, color=color, markeredgecolor=color,
                          ls='',
                          picker=settings.plot['picker_tol'])

        # TODO: Results and break points

    def plot(self):
        """ Matplotlib plot of time series
        """
        # Clear before plotting again
        self.axes.clear()

        # Setup axes
        if tsm.ts:
            self.axes.set_title(tsm.ts.pixel_pos)
        self.axes.set_xlabel('Date')
        self.axes.set_ylabel('Value')  # TODO

        self.axes.set_xlim(dt.date(settings.plot['x_min'], 01, 01),
                           dt.date(settings.plot['x_max'], 01, 01))

        self.axes.set_ylim(settings.plot['y_min'][0],
                           settings.plot['y_max'][0])

        # Plot -- axis 1
        added = np.where(settings.plot['y_axis_1_band'])[0]
        if added.size > 0:
            for _added in added:
                _series = settings.plot_series[_added]
                _band = settings.plot_band_indices[_added]

                self._plot_series(self.axes, _added, _series, _band)

        # Redraw
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def disconnect(self):
        pass
