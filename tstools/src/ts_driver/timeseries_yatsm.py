""" A basic timeseries driver for running YATSM on stacked timeseries
"""
from datetime import datetime as dt
import itertools
import logging
import re

import matplotlib as mpl
import numpy as np
import patsy
import sklearn
import sklearn.externals.joblib as jl

from . import timeseries_stacked
from .timeseries import Series
from .ts_utils import find_files, parse_landsat_MTL
from .. import settings

logger = logging.getLogger('tstools')


class YATSMTimeSeries(timeseries_stacked.StackedTimeSeries):
    """ Timeseries driver for YATSM algorithm
    """
    description = 'YATSM CCDCesque Timeseries'
    location = None
    mask_values = np.array([2, 3, 4, 255])

    # Driver configuration
    _stack_pattern = 'L*stack'
    _date_index = [9, 16]
    _date_format = '%Y%j'
    _cache_folder = 'cache'
    _results_folder = 'YATSM'
    _results_pattern = 'yatsm_r*'
    _mask_band = [8]
    _min_values = [0]
    _max_values = [10000]
    _metadata_file_pattern = 'L*MTL.txt'
    _calc_pheno = False

    config = ['_stack_pattern',
              '_date_index',
              '_date_format',
              '_cache_folder',
              '_results_folder',
              '_results_pattern',
              '_mask_band',
              '_min_values', '_max_values',
              '_metadata_file_pattern',
              '_calc_pheno']
    config_names = [
        'Stack pattern',
        'Date index',
        'Date format',
        'Cache folder',
        'Results folder',
        'Results pattern',
        'Mask band',
        'Min data values', 'Max data values',
        'Metadata file pattern',
        'LTM phenology']

    # Driver controls
    _calculate_live = True
    _consecutive = 5
    _min_obs = 16
    _threshold = 4.0
    _enable_min_rmse = True
    _min_rmse = 100
    _design = '1 + x + harm(x, 1)'
    _test_indices = np.array([2, 3, 4, 5])
    _dynamic_rmse = True
    _screen_crit = 400.0
    _remove_noise = True
    _reverse = False
    _robust_results = False
    _commit_test = False
    _commit_alpha = 0.01

    # Requires YATSM>=v0.5.0
    _regression_type = 'sklearn_Lasso20'

    controls_title = 'YATSM Algorithm Options'
    controls = [
        '_calculate_live',
        '_consecutive',
        '_min_obs',
        '_threshold',
        '_enable_min_rmse',
        '_min_rmse',
        '_design',
        '_test_indices',
        '_dynamic_rmse',
        '_screen_crit',
        '_remove_noise',
        '_reverse',
        '_regression_type',
        '_robust_results',
        '_commit_test',
        '_commit_alpha']
    controls_names = [
        'Calculate live',
        'Consecutive',
        'Min Observations',
        'Threshold',
        'Use min RMSE?',
        'Min RMSE',
        'Design',
        'Test indices',
        'Dynamic RMSE',
        'Screening critical value',
        'Remove noise',
        'Run in reverse',
        'Regression type',
        'Robust results',
        'Commission test',
        'Commission test alpha']

    def __init__(self, location, config=None):
        super(YATSMTimeSeries, self).__init__(location, config=config)

        # Check for YATSM imports
        self._check_yatsm()
        # Find extra metadata
        self._init_metadata()

        # Setup YATSM
        self.yatsm_model = None
        self.X = None
        self.Y = None
        self.coef_name = 'coef'

        # Setup min/max values
        if len(self._min_values) == 1:
            self._min_values = self._min_values * (self.series[0].count - 1)
        if len(self._max_values) == 1:
            self._max_values = self._max_values * (self.series[0].count - 1)
        self._min_values = np.asarray(self._min_values)
        self._max_values = np.asarray(self._max_values)

    def set_custom_controls(self, values):
        logger.debug('Setting custom values')
        for v, k in zip(values, self.controls):
            current_value = getattr(self, k)
            if isinstance(v, type(current_value)):
                setattr(self, k, v)
            else:
                # Make an exception for minimum RMSE since we can pass None
                if k == 'min_rmse' and isinstance(v, float):
                    setattr(self, k, v)
                else:
                    msg = 'Could not set {k} to {v} (current: {c})'.format(
                        k=k, v=v, c=current_value)
                    raise Exception(msg)

    def fetch_results(self):
        """ Read or calculate results for current pixel """
        if self._calculate_live:
            self._fetch_results_live()
        else:
            self._fetch_results_saved()

        # Update multitemporal screening metadata
        if self.yatsm_model:
            self.series[0].multitemp_screened = \
                np.in1d(self.X[:, 1], self.yatsm_model.X[:, 1],
                        invert=True).astype(np.uint8)
            if self._calc_pheno:
                for rec in self.yatsm_model.record:
                    # Find dates in record
                    idx = np.where(
                        (self.series[0].images['ordinal'] >= rec['start']) &
                        (self.series[0].images['ordinal'] <= rec['end']))[0]
                    # Put observations into SPR/SUM/AUT
                    _spr = np.where(self.series[0].images['doy'][idx] <=
                                    rec['spring_doy'])[0]
                    _sum = np.where((self.series[0].images['doy'][idx] >
                                     rec['spring_doy']) &
                                    (self.series[0].images['doy'][idx] <
                                     rec['autumn_doy']))[0]
                    _aut = np.where(self.series[0].images['doy'][idx] >=
                                    rec['autumn_doy'])[0]
                    self.series[0].pheno[idx[_spr]] = 'SPR'
                    self.series[0].pheno[idx[_sum]] = 'SUM'
                    self.series[0].pheno[idx[_aut]] = 'AUT'

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
        if self.yatsm_model is None or len(self.yatsm_model.record) == 0:
            return
        if band >= self.yatsm_model.record[self.coef_name].shape[2]:
            logger.debug('Not results for band %i' % band)
            return

        # Setup output
        mx = []
        my = []

        # Don't predict with any categorical information
        design = re.sub(r'[\+\-][\ ]+C\(.*\)', '', self._design)
        coef_columns = []
        for k, v in self._design_info.column_name_indexes.iteritems():
            if not re.match('C\(.*\)', k):
                coef_columns.append(v)
        coef_columns = np.asarray(coef_columns)

        for rec in self.yatsm_model.record:
            # Check for reverse
            if rec['end'] < rec['start']:
                i_step = -1
            else:
                i_step = 1
            # Date range to predict
            if dates is not None:
                end = max(rec['break'], rec['end'])
                _mx = dates[np.where((dates >= rec['start']) &
                                     (dates <= end))[0]]
            else:
                _mx = np.arange(rec['start'], rec['end'], i_step)

            if _mx.size == 0:
                continue
            # Coefficients to use for prediction
            _coef = rec[self.coef_name][coef_columns, band]
            # Setup design matrix
            _mX = patsy.dmatrix(design, {'x': _mx}).T
            # Predict
            _my = np.dot(_coef, _mX)
            # Transform ordinal back to datetime for plotting
            _mx = np.array([dt.fromordinal(int(_x)) for _x in _mx])

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
        if self.yatsm_model is None:
            return
        # Setup output
        bx = []
        by = []

        if len(self.yatsm_model.record) > 0:
            for rec in self.yatsm_model.record:
                if rec['break'] != 0:
                    _bx = dt.fromordinal(int(rec['break']))
                    index = np.where(self.series[series].images['date']
                                     == _bx)[0]
                    if (index.size > 0 and
                            index[0] < self.series[series].data.shape[1]):
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
        if self.yatsm_model is None:
            return
        rx, ry = [], []

        X, y = self.get_data(series, band, mask=settings.plot['mask'])
        predict = self.get_prediction(series, band, dates=X['ordinal'])
        if predict is None:
            return
        date, yhat = predict

        for _date, _yhat in zip(date, yhat):
            idx = np.in1d(X['date'], _date)
            resid = y[idx] - _yhat

            rx.append(_date)
            ry.append(resid)

        return rx, ry

    def get_plot(self, series, band, axis, desc):
        """ Plot some information on an axis for a plot of some description

        Args:
          series (int): index of Series for residuals
          band (int): index of band to return
          axis (matplotlib.axes._subplots.Axes): a matplotlib axis to plot on
          desc (str): description of plot, usually a plot class from
            `tstools.plots`

        Returns:
          iterable: list of artists to include in legend

        """
        artists = []
        if desc == 'TSPlot':
            for rec in self.yatsm_model.record:
                _x = (rec['start'] + rec['end']) / 2.0
                _x, _y = self.get_prediction(series, band,
                                             dates=np.array([_x]))
                _x = _x[0][0]
                _y = _y[0][0] + 250
                axis.text(_x, _y, 'RMSE: %.3f' % rec['rmse'][band],
                          fontsize=18,
                          horizontalalignment='center')
        elif desc == 'DOYPlot':
            names = self.yatsm_model.record.dtype.names
            if self._calc_pheno and all([r in names for r in
                                         ('spring_doy', 'autumn_doy')]):
                colors = mpl.cm.Set1(np.linspace(0, 1, 9))[:, :-1]

                color_cycle = itertools.cycle(colors)
                for i, rec in enumerate(self.yatsm_model.record):
                    col = [c for c in color_cycle.next()]
                    artists.append(
                        axis.axvline(rec['spring_doy'], label='Model %i' % i,
                                     c=col, lw=2)
                    )
                    axis.axvline(rec['autumn_doy'], label='Model %i' % i,
                                 c=col, lw=2)

        return artists

# RESULTS HELPER METHODS
    def _fetch_results_saved(self):
        """ Read YATSM results and return """
        raise NotImplementedError('No saved results reading just yet...')

    def _fetch_results_live(self):
        """ Run YATSM and get results """
        logger.debug('Calculating YATSM results on the fly')
        # Setup design matrix, Y, and dates
        self.X = patsy.dmatrix(self._design,
                               {
                                   'x': self.series[0].images['ordinal'],
                                   'sensor': self.series[0].sensor,
                                   'pr': self.series[0].pathrow
                               })
        self._design_info = self.X.design_info
        self.Y = self.series[0].data.astype(np.int16)
        self.dates = np.asarray(self.series[0].images['ordinal'])

        mask = self.Y[self._mask_band[0] - 1, :]
        Y_data = np.delete(self.Y, self._mask_band[0] - 1, axis=0)

        # Mask out masked values
        clear = np.in1d(mask, self.mask_values, invert=True)
        valid = get_valid_mask(Y_data,
                               self._min_values,
                               self._max_values).astype(np.bool)
        clear *= valid
        # Setup Y

        # Setup parameters
        lm = sklearn.linear_model.Lasso(alpha=20)
        reg = self._regression_type
        print(self._regression_type)
        if hasattr(yatsm.regression, 'packaged'):
            if reg in yatsm.regression.packaged.packaged_regressions:
                reg_fn = yatsm.regression.packaged.find_packaged_regressor(reg)
                try:
                    lm = jl.load(reg_fn)
                except:
                    logger.error('Cannot load regressor: %s' % reg)
                else:
                    logger.debug('Loaded regressor %s from %s' % (reg, reg_fn))
            else:
                logger.error('Cannot use unknown regression %s' % reg)
        else:
            logger.warning('Using failsafe Lasso(lambda=20) from scikit-learn. '
                           'Upgrade to yatsm>=0.5.1 to access more regressors.')

        kwargs = dict(
            test_indices=self._test_indices,
            consecutive=self._consecutive,
            threshold=self._threshold,
            min_obs=self._min_obs,
            min_rmse=None if self._enable_min_rmse else self._min_rmse,
            screening_crit=self._screen_crit,
            remove_noise=self._remove_noise,
            dynamic_rmse=self._dynamic_rmse,
        )

        self.yatsm_model = CCDCesque(lm=lm, **kwargs)
        # Don't want to have DEBUG logging when we run YATSM
        log_level = logger.level
        logger.setLevel(logging.INFO)

        if self._reverse:
            self.yatsm_model.fit(
                np.flipud(self.X[clear, :]),
                np.fliplr(Y_data[:, clear]),
                np.fliplr(self.dates[clear]))
        else:
            self.yatsm_model.fit(
                self.X[clear, :],
                Y_data[:, clear],
                self.dates[clear])

        if self._commit_test:
            self.yatsm_model.record = postprocess.commission_test(
                self.yatsm_model, self._commit_alpha)

        # if self._robust_results:
        #     self.coef_name = 'robust_coef'
        #     self.yatsm_model.record = postprocess.refit_record(
        #         self.yatsm_model, 'robust'
        # else:
        #     self.coef_name = 'coef'

        if self._calc_pheno:
            # TODO: parameterize band indices & scale factor
            ltm = pheno.LongTermMeanPhenology()
            self.yatsm_model.record = ltm.fit(self.yatsm_model)

        # Restore log level
        logger.setLevel(log_level)

# SETUP
    def _init_metadata(self):
        """ Setup metadata for series """
        # Find MTL file
        self.mtl_files = None
        if self._metadata_file_pattern:
            search = find_files(self.location, self._metadata_file_pattern,
                                ignore_dirs=[self._results_folder])
            if len(search) == 0:
                logger.error(
                    'Could not find image metadata with pattern {p}'.format(
                        p=self._metadata_file_pattern))
            if len(search) != len(self.series[0].images['date']):
                logger.error('Inconsistent number of metadata files found: '
                             '{0} images vs {1} metadata files)'.format(
                                len(self.series[0].images['date']),
                                len(search)))
            else:
                self.mtl_files = search

        # Setup metadata for series
        self.series[0].metadata = ['sensor', 'pathrow', 'multitemp_screened']
        self.series[0].metadata_names = ['Sensor', 'Path/Row',
                                         'Multitemp Screened']
        self.series[0].metadata_table = [False, False, False]

        # Sensor ID
        self.series[0].sensor = np.array([n[0:3] for n in
                                          self.series[0].images['filename']])
        # Path/row
        self.series[0].pathrow = np.array([
            'p{p}r{r}'.format(p=n[3:6], r=n[6:9]) for
            n in self.series[0].images['filename']])
        # Multitemporal noise screening - init to 0 (not screened)
        #   Will update this during model fitting
        self.series[0].multitemp_screened = np.ones(self.series[0].n)
        # Make an entry 0 so we get this in the unique values
        self.series[0].multitemp_screened[0] = 0

        # If we found MTL files, find cloud cover
        if self.mtl_files is not None:
            self.series[0].metadata.append('cloud_cover')
            self.series[0].metadata_names.append('Cloud cover')
            self.series[0].metadata_table.append(True)
            self.series[0].cloud_cover = np.zeros(self.series[0].n)
            for i, mtl_file in enumerate(self.mtl_files):
                self.series[0].cloud_cover[i] = parse_landsat_MTL(
                    mtl_file, 'CLOUD_COVER')

        if self._calc_pheno:
            self.series[0].metadata.append('pheno')
            self.series[0].metadata_names.append('Phenology')
            self.series[0].metadata_table.append(False)
            # Initialize almost all as summer (SUM); first two as SPR/AUT
            self.series[0].pheno = np.repeat('SUM', self.series[0].n)
            self.series[0].pheno[0] = 'SPR'
            self.series[0].pheno[1] = 'AUT'

    def _check_yatsm(self):
        """ Check if YATSM is available
        """
        try:
            global yatsm
            global CCDCesque, postprocess
            global harm
            global get_valid_mask
            import yatsm
            from yatsm.algorithms import CCDCesque, postprocess
            from yatsm._cyprep import get_valid_mask
            from yatsm.regression.transforms import harm
        except ImportError as e:
            raise ImportError('Could not import YATSM because it could not '
                              'import a dependency (%s)' % e.message)
        except:
            raise ImportError('Could not import YATSM for an unknown reason '
                              '(%s)' % e.message)
        else:
            self.has_results = True

        if self._calc_pheno:
            try:
                global pheno
                import yatsm.phenology.longtermmean as pheno
            except:
                msg = ('Could not import YATSM phenology module. '
                       'Make sure you have R and rpy2 installed.')
                raise ImportError(msg)
