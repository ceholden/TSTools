""" A basic timeseries driver for reading CCDC results
"""
import datetime as dt
import logging
import os

import numpy as np
has_scipy = True
try:
    import scipy.io as spio
except:
    has_scipy = False

from . import timeseries_stacked  # noqa
from ..ts_utils import ConfigItem, find_files  # noqa
from ... import settings  # noqa

logger = logging.getLogger('tstools')


def ml2ordinal(d):
    """ Return ordinal date of MATLAB datenum

    Args:
        d (int): MATLAB date

    Return:
        int: ordinal date
    """
    return (dt.datetime.fromordinal(d) - dt.timedelta(days=366)).toordinal()


class CCDCTimeSeries(timeseries_stacked.StackedTimeSeries):
    """ Reader for CCDC pre-calculated results for a 'stacked' timeseries

    This driver requires the following Python packages in addition to basic
    TSTools package dependencies:

    * `scipy`: <a href="http://www.scipy.org/scipylib/index.html">scipy</a>
    """

    description = 'CCDC Results Reader'
    has_results = True

    ccdc_results = None

    # Driver configuration
    config = timeseries_stacked.StackedTimeSeries.config.copy()
    config['results_folder'] = ConfigItem('Results folder', 'TSFitMap')

    def __init__(self, location, config=None):
        if not has_scipy:
            raise ImportError('Cannot import "scipy" module required to read '
                              'CCDC results files')
        super(CCDCTimeSeries, self).__init__(location, config=config)

    def fetch_results(self):
        """ Read results for current pixel
        """
        path = os.path.join(self.location, self.config['results_folder'].value)
        row = self.series[0].py + 1

        result = find_files(path, 'record_change%s.mat' % row)
        if not result:
            logger.error('Could not find result for row %s' % row)
            return

        ccdc_results = spio.loadmat(result[0], squeeze_me=True)['rec_cg']
        pos = self.series[0].py * self.series[0].width + self.series[0].px + 1

        pos_search = np.where(ccdc_results['pos'] == pos)[0]

        if pos_search.size == 0:
            logger.error('Could not find result for row %s col %s' %
                         (row, self.series[0].px + 1))
            return
        self.ccdc_results = ccdc_results[pos_search]

    def get_prediction(self, series, band, dates=None):
        """ Return prediction for a given band

        Args:
          series (int): index of Series used for prediction
          band (int): index of band to return
          dates (iterable): list or np.ndarray of ordinal dates to predict; if
            None, predicts for every date within timeseries (default: None)

        Returns:
          iterable: sequence of tuples (1D NumPy arrays, x and y) containing
            predictions

        """
        if series > 0:
            return
        if self.ccdc_results is None or len(self.ccdc_results) == 0:
            return

        if band >= self.ccdc_results['coefs'][0].shape[1]:
            logger.debug('Not results for band %i' % band)
            return

        def make_X(x):
            w = 2 * np.pi / 365.25
            return np.vstack((np.ones_like(x),
                              x,
                              np.cos(w * x), np.sin(w * x),
                              np.cos(2 * w * x), np.sin(2 * w * x),
                              np.cos(3 * w * x), np.sin(3 * w * x)))

        mx, my = [], []
        for rec in self.ccdc_results:
            if rec['t_end'] < rec['t_start']:
                i_step = -1
            else:
                i_step = 1

            start = ml2ordinal(rec['t_start'])
            if dates is not None:
                end = ml2ordinal(max(rec['t_break'], rec['t_end']))
                _mx = dates[np.where((dates >= start) & (dates <= end))[0]]
            else:
                end = ml2ordinal(rec['t_end'])
                _mx = np.arange(start, end, i_step)

            # Coefficients used for prediction
            _coef = rec['coefs'][:, band]
            _mX = make_X(_mx)

            _my = np.dot(_coef, _mX[:_coef.size, :])
            # Transform ordinal back to datetime for plotting
            _mx = np.array([dt.datetime.fromordinal(int(_x))
                            for _x in _mx])

            mx.append(_mx)
            my.append(_my)

        return mx, my

    def get_breaks(self, series, band):
        """ Return break points for a given band

        Args:
          series (int): index of Series for prediction
          band (int): index of band to return

        Returns:
          iterable: sequence of tuples (1D NumPy arrays, x and y) containing
            break points

        """
        if self.ccdc_results is None:
            return

        # Setup output
        bx = []
        by = []

        n_obs = self.series[series].data.shape[1]

        if len(self.ccdc_results) > 0:
            for rec in self.ccdc_results:
                if rec['t_break'] != 0:
                    _bx = dt.datetime.fromordinal(ml2ordinal(rec['t_break']))
                    index = np.where(self.series[series].images['date'] ==
                                     _bx)[0]
                    if (index.size > 0 and index[0] < n_obs):
                        bx.append(_bx)
                        by.append(self.series[series].data[band, index[0]])
                    else:
                        logger.warning('Could not determine breakpoint')

        return bx, by

    def get_residuals(self, series, band):
        """ Return model residuals (y - predicted yhat) for a given band

        Args:
          series (int): index of Series for residuals
          band (int): index of band to return

        Returns:
          iterable: sequence of tuples (1D NumPy arrays, x and y) containing
            residual dates and values

        """
        if self.ccdc_results is None:
            return

        rx, ry = [], []

        X, y = self.get_data(series, band, mask=settings.plot['mask'])
        date, yhat = self.get_prediction(series, band, dates=X['ordinal'])

        for _date, _yhat in zip(date, yhat):
            idx = np.in1d(X['date'], _date)
            if idx.size == 0:
                logger.warning('Could not plot residuals for a model')
                continue
            resid = y[idx] - _yhat

            rx.append(_date)
            ry.append(resid)

        return rx, ry
