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
        super(TSPlot, self).__init__()
        # Location of pixel plotted
        self.title = ''

        # Add second axis
        self.axis_2 = self.axis_1.twinx()
        self.axis_2.xaxis.set_visible(False)
        self.axes.append(self.axis_2)

        # Setup plots
        self.plot()

    def _plot_series(self, axis, idx, series, band):
        """ Plot a timeseries from a timeseries ts_driver

        Args:
          axis (mpl.axes.Axes): axis to plot
          idx (int): index of all available plotting bands
          series (int): index of series within timeseries driver
          band (int): index of band within series within timeseries driver

        """
        # Iterate over symbology descriptions
        for index, marker, color in zip(settings.plot_symbol[idx]['indices'],
                                        settings.plot_symbol[idx]['markers'],
                                        settings.plot_symbol[idx]['colors']):
            # Any points falling into this category?
            if index.size > 0:
                x, y = tsm.ts.get_data(series, band,
                                       mask=settings.plot['mask'],
                                       indices=index)

                color = [c / 255.0 for c in color]
                axis.plot(x, y,
                          marker=marker, color=color, markeredgecolor=color,
                          ls='',
                          picker=settings.plot['picker_tol'])

        if settings.plot['fit']:
            predict = tsm.ts.get_prediction(series, band)
            if predict is not None:
                px, py = predict[0], predict[1]
                for _px, _py in zip(px, py):
                    axis.plot(_px, _py, linewidth=2)

        if settings.plot['break']:
            breaks = tsm.ts.get_breaks(series, band)
            if breaks is not None:
                bx, by = breaks[0], breaks[1]
                for _bx, _by in zip(bx, by):
                    axis.plot(_bx, _by, 'ro',
                              mec='r', mfc='none', ms=10, mew=5)

        # Reset color cycle for later
        axis.set_color_cycle(None)

    def plot(self):
        """ Matplotlib plot of time series
        """
        # Clear before plotting again
        self.axis_1.clear()
        self.axis_2.clear()

        # TODO: put axis_2 y-ticks on same grid as axis_1

        # Setup axes
        if tsm.ts:
            self.axis_1.set_title(tsm.ts.pixel_pos)
        self.axis_1.set_xlabel('Date')
        self.axis_1.set_ylabel('Value')  # TODO

        self.axis_1.set_xlim(dt.date(settings.plot['x_min'], 01, 01),
                             dt.date(settings.plot['x_max'], 01, 01))

        self.axis_1.set_ylim(settings.plot['y_min'][0],
                             settings.plot['y_max'][0])
        self.axis_2.set_ylim(settings.plot['y_min'][1],
                             settings.plot['y_max'][1])

        # Plot -- axis 1
        added = np.where(settings.plot['y_axis_1_band'])[0]
        if added.size > 0:
            for _added in added:
                _series = settings.plot_series[_added]
                _band = settings.plot_band_indices[_added]

                self._plot_series(self.axis_1, _added, _series, _band)

        added = np.where(settings.plot['y_axis_2_band'])[0]
        if added.size > 0:
            for _added in added:
                _series = settings.plot_series[_added]
                _band = settings.plot_band_indices[_added]

                self._plot_series(self.axis_2, _added, _series, _band)

        # Redraw
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def disconnect(self):
        pass
