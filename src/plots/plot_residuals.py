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
        # Get residuals and concatenate across timeseries segments
        residuals = tsm.ts.get_residuals(series, band)
        if residuals is None:
            return
        resid_dates = np.concatenate(residuals[0])
        resid_values = np.concatenate(residuals[1])

        # Iterate over symbology descriptions
        for index, marker, color in zip(settings.plot_symbol[idx]['indices'],
                                        settings.plot_symbol[idx]['markers'],
                                        settings.plot_symbol[idx]['colors']):
            if index.size == 0:
                continue
            X, y = tsm.ts.get_data(series, band,
                                   mask=settings.plot['mask'],
                                   indices=index)
            if y.size == 0:
                continue

            color = [c / 255.0 for c in color]

            # Find residuals inside this symbology description
            idx = np.in1d(resid_dates, X['date'])
            if idx.size == 0:
                continue

            axis.plot(resid_dates[idx], resid_values[idx],
                      marker=marker, color=color, markeredgecolor=color,
                      ls='', picker=settings.plot['picker_tol'])

        if settings.plot['break']:
            breaks = tsm.ts.get_breaks(series, band)
            if breaks is not None:
                bx = breaks[0]
                for _bx in bx:
                    idx = np.where(resid_dates == _bx)[0][0]
                    axis.plot(_bx, resid_values[idx], 'ro',
                              mec='r', mfc='none', ms=10, mew=5)

        if settings.plot['custom']:
            try:
                tsm.ts.get_plot(series, band, axis, self.__class__.__name__)
            except Exception as e:
                logger.error('Could not plot TS driver customized plot info: '
                             '%s' % e.message)


        # Reset color cycle for later
        axis.set_color_cycle(None)

    def plot(self):
        """ Plot residuals
        """
        logger.debug('Plotting Residual plot')
        # Clear before plotting again
        self.axis_1.clear()
        self.axis_2.clear()

        if tsm.ts:
            self.axis_1.set_title(tsm.ts.pixel_pos)
        self.axis_1.set_xlabel('Date')
        self.axis_1.set_ylabel(r'Residuals ($y - \hat{y}$)')

        self.axis_1.set_xlim(dt.date(settings.plot['x_min'], 01, 01),
                             dt.date(settings.plot['x_max'], 01, 01))

        # Add 0 line
        self.axis_1.axhline(y=0, xmin=0, xmax=1, c='k')
        self.axis_2.axhline(y=0, xmin=0, xmax=1, c='k')

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
