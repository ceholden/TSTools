""" "Day of Year" (DOY) plot

DOY plot shows within-year variation in the data on the X axis and across-year
variation in the data using a color ramp.
"""
from datetime import datetime as dt
import logging
import os

import matplotlib as mpl
import matplotlib.cm
import mpl_toolkits.axes_grid1 as mpl_grid
import numpy as np
try:
    import palettable
    HAS_PALETTABLE = True
except:
    HAS_PALETTABLE = False

from . import base_plot
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm
from .. import settings

logger = logging.getLogger('tstools')


class DOYPlot(base_plot.BasePlot):

    def __str__(self):
        return "Stacked Day of Year Plot"

    def __init__(self, parent=None):
        super(DOYPlot, self).__init__()

        # Colormap -- try to load from environment
        cmap = os.environ.get('TSTOOLS_DOY_CMAP', 'perceptual_rainbow_16')
        if HAS_PALETTABLE:
            if hasattr(palettable.colorbrewer, cmap):
                self.cmap = getattr(palettable.colorbrewer, cmap).mpl_colormap
            elif hasattr(palettable.cubehelix, cmap):
                self.cmap = getattr(palettable.cubehelix, cmap).mpl_colormap
            else:
                logger.error('Cannot find colormap %s for DOY plot colormap. '
                             'Using cubehelix from matplotlib as backup.'
                             % cmap)
                self.cmap = mpl.cm.cubehelix
        else:
            logger.warning('`palettable` is not installed. Using cubehelix '
                           'from matplotlib as backup for DOY plot colormap')
            self.cmap = mpl.cm.cubehelix

        self.reset()
        self.plot()

    def reset(self):
        """ Resets variables pertinent to making a plot

        Useful for reconfiguring existing plot object for new timeseries
        """
        # Setup colormap
        if tsm.ts:
            yr_min, yr_max = float('inf'), float('-inf')
            for series in tsm.ts.series:
                year = np.array([d.year for d in series.images['date']])
                if year.min() <= yr_min:
                    yr_min = year.min()
                if year.max() >= yr_max:
                    yr_max = year.max()
        else:
            yr_min, yr_max = dt.today().year, dt.today().year + 1

        self.norm = mpl.colors.Normalize(vmin=yr_min, vmax=yr_max)
        self.mapper = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)

        self.cm = mpl.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)
        self.cm.set_array([yr_min, yr_max])

    def _plot_series(self, idx, series, band):
        """ Plot a timeseries from a timeseries ts_driver

        Args:
            idx (int): index of all available plotting bands
            series (int): index of series within timeseries driver
            band (int): index of band within series within timeseries driver

        """
        logger.debug('Plotting DOY plot series')
        for index, marker in zip(settings.plot_symbol[idx]['indices'],
                                 settings.plot_symbol[idx]['markers']):
            # Any points falling into this category?
            if index.size == 0:
                continue

            # Get data and extract DOY and year
            X, y = tsm.ts.get_data(series, band,
                                   mask=settings.plot['mask'],
                                   indices=index)

            doy = X['doy']
            year = np.array([d.year for d in X['date']])

            # Check for year range
            year_in = np.where((year >= settings.plot['x_min']) &
                               (year <= settings.plot['x_max']))[0]

            # Plot
            self.axis_1.scatter(doy[year_in], y[year_in],
                                cmap=self.cmap, c=year[year_in],
                                norm=self.norm,
                                marker=marker, edgecolors='none', s=35,
                                picker=settings.plot['picker_tol'])

        # TODO: prediction & breaks
        if settings.plot['custom']:
            try:
                artists = tsm.ts.get_plot(series, band, self.axis_1,
                                          self.__class__.__name__)
                if artists:
                    leg = self.axis_1.legend(handles=artists)
                    leg.draggable(state=True)
            except Exception as e:
                logger.error('Could not plot TS driver customized plot info: '
                             '%s' % e.message)

    def plot(self):
        logger.debug('Plotting DOY plot')
        self.axis_1.clear()

        # Setup axes
        if tsm.ts:
            self.axis_1.set_title(tsm.ts.pixel_pos)

        self.axis_1.set_xlabel('Day of Year')
        self.axis_1.set_ylabel('Value')

        added = np.where(settings.plot['y_axis_1_band'])[0]
        if added.size > 0:
            for _added in added:
                _series = settings.plot_series[_added]
                _band = settings.plot_band_indices[_added]
                self._plot_series(_added, _series, _band)

        # Legend
        if tsm.ts is not None:
            # Setup layout to add space
            # http://matplotlib.org/mpl_toolkits/axes_grid/users/overview.html#axesdivider
            divider = mpl_grid.make_axes_locatable(self.axis_1)
            cax = divider.append_axes('right', size='5%', pad=0.05)
            if getattr(self, 'cbar', None) is not None:
                self.fig.delaxes(self.fig.axes[1])
                self.fig.subplots_adjust(right=0.90)
            self.cbar = self.fig.colorbar(self.cm, cax=cax)

        self.axis_1.set_xlim((1, 366))
        self.axis_1.set_ylim(settings.plot['y_min'][0],
                             settings.plot['y_max'][0])

        self.fig.tight_layout()
        self.fig.canvas.draw()
        logger.debug('Done plotting DOY plot')

    #     if settings.plot['fit'] is True:
    #         med_year = []
    #         fit_plt = []
    #         # Find median year and plot that result
    #         for n, _yr in enumerate(self.mx_year):
    #             # Make sure _yr is not empty array
    #             if len(_yr) == 0:
    #                 continue
    #             # Determine median year
    #             med = int(np.median(_yr))
    #             # Make sure median year is in our current x-axis
    #             if settings.plot['xmin'] > med or settings.plot['xmax'] < med:
    #                 continue
    #             med_year.append(med)

    #             # Determine line color
    #             col = mapper.to_rgba(med)

    #             # Get index from mx predicted data for median year
    #             fit_range = np.arange(
    #                 np.where(_yr == med)[0][0],
    #                 np.where(_yr == med)[0][-1])

    #             # Recreate as DOY
    #             mx_doy = np.array([int(d.strftime('%j')) for d in
    #                                self.mx[n][fit_range]])

    #             # Plot
    #             seg, = self.axes.plot(mx_doy, self.my[n][fit_range],
    #                                   color=col, linewidth=2)
    #             fit_plt.append(seg)

    #         if len(med_year) > 0:
    #             self.axes.legend(fit_plt,
    #                              ['Fit {n}: {y}'.format(n=n + 1, y=y)
    #                               for n, y in enumerate(med_year)])
    def disconnect(self):
        pass
