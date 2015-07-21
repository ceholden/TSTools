""" Plot for model residuals for timeseries that have predictions
"""
import datetime as dt
import logging

import numpy as np

from . import base_plot
from .. import settings
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


class ResidualPlot(base_plot.BasePlot):
    """ Plot timeseries residuals residuals ~ date for drivers with predictions
    """

    def __str__(self):
        return "Residual Plot"

    def __init__(self, parent=None):
        super(ResidualPlot, self).__init__()
        # Add second axis
        self.axis_2 = self.axis_1.twinx()
        self.axis_2.xaxis.set_visible(False)
        self.axes.append(self.axis_2)

        # Setup plots
        self.plot()

    def reset(self):
        """ Resets variables pertinent to making a plot

        Useful for reconfiguring existing plot object for new timeseries
        """
        # Nothing to do
        pass

    def _plot_series(self, axis, idx, series, band):
        """ Plot a residuals from a timeseries ts_driver

        Args:
          axis (mpl.axes.Axes): axis to plot
          idx (int): index of all available plotting bands
          series (int): index of series within timeseries driver
          band (int): index of band within series within timeseries driver

        """
        logger.debug('Plotting Residual plot series')
        # Iterate over symbology descriptions
        for index, marker, color in zip(settings.plot_symbol[idx]['indices'],
                                        settings.plot_symbol[idx]['markers'],
                                        settings.plot_symbol[idx]['colors']):
            if index.size == 0:
                continue
            X, y = tsm.ts.get_data(series, band,
                                   mask=settings.plot['mask'],
                                   indices=index)
            date, yhat = tsm.ts.get_prediction(series, band,
                                               dates=X['ordinal'])
            if yhat is None:
                return

            for _date, _yhat in zip(date, yhat):
                idx = np.in1d(X['date'], _date)

                resid = _yhat - y[idx]

                color = [c / 255.0 for c in color]
                axis.plot(_date, resid,
                          marker=marker, color=color, markeredgecolor=color,
                          ls='',
                          picker=settings.plot['picker_tol'])

    def plot(self):
        """ Plot residuals
        """
        # from PyQt4 import QtCore
        # QtCore.pyqtRemoveInputHook()
        # from IPython.core.debugger import Pdb
        # Pdb().set_trace()
        logger.debug('Plotting Residual plot')
        # Clear before plotting again
        self.axis_1.clear()
        self.axis_2.clear()

        if tsm.ts:
            self.axis_1.set_title(tsm.ts.pixel_pos)
        self.axis_1.set_xlabel('Date')
        self.axis_1.set_ylabel('Residuals')

        self.axis_1.set_xlim(dt.date(settings.plot['x_min'], 01, 01),
                             dt.date(settings.plot['x_max'], 01, 01))

        self.axis_1.set_ylim(settings.plot['y_min'][0],
                             settings.plot['y_max'][0])
        self.axis_2.set_ylim(settings.plot['y_min'][1],
                             settings.plot['y_max'][1])

        # Plot -- axis 1
        if not tsm.ts or not tsm.ts.has_results:
            logger.debug('Not plotting residuals -- driver has no results')
            self.fig.tight_layout()
            self.fig.canvas.draw()
            return

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
        logger.debug('Done plotting Residual plot')
