""" A basic timeseries driver for running YATSM on stacked timeseries
"""
from collections import OrderedDict
from datetime import datetime as dt
import itertools
import logging
import os
import re

import matplotlib as mpl
import numpy as np
import patsy
import sklearn
import sklearn.externals.joblib as jl

from . import timeseries_stacked
from ..ts_utils import ConfigItem, find_files, parse_landsat_MTL
from ... import settings
from ...logger import qgis_log

logger = logging.getLogger('tstools')


# Try to import yatsm dependency
has_yatsm = False
has_yatsm_pheno = False
try:
    import yatsm
    from yatsm.algorithms import CCDCesque, postprocess
    from yatsm._cyprep import get_valid_mask
    from yatsm.regression.transforms import harm  # noqa
    from yatsm.utils import get_output_name
    from ..mixins.yatsm_ccdcesque import version_kwargs
except ImportError as e:
    has_yatsm_msg = ('Could not import YATSM because it could not '
                     'import a dependency ({})'.format(e))
except Exception as e:
    has_yatsm_msg = ('Could not import YATSM for an unknown reason '
                     '({})'.format(e))
else:
    has_yatsm = True
    try:
        import yatsm.phenology.longtermmean as pheno
    except Exception as e:
        has_yatsm_pheno_msg = ('Could not import YATSM phenology module '
                               'because it could not import a dependency ({})'
                               .format(e))
    else:
        has_yatsm_pheno = True


class YATSMTimeSeries(timeseries_stacked.StackedTimeSeries):
    """ Timeseries driver for CCDCesque algorithm implemented in YATSM

    Requires a working installation of YATSM. For more information, visit
    the [YATSM Github website](https://github.com/ceholden/yatsm).

    This driver requires the following Python packages in addition to basic
    TSTools package dependencies:

    * [`scikit-learn`](http://scikit-learn.org/stable/)
    * [`patsy`](https://patsy.readthedocs.org/en/latest/)
    * [`yatsm`](https://github.com/ceholden/yatsm)
    """
    description = 'YATSM CCDCesque Timeseries'
    location = None
    mask_values = np.array([2, 3, 4, 255])
    has_results = True

    # Driver configuration
    config = OrderedDict((
        ('stack_pattern', ConfigItem('Stack pattern', 'L*stack')),
        ('date_index', ConfigItem('Date index', [9, 16])),
        ('date_format', ConfigItem('Date format', '%Y%j')),
        ('cache_folder', ConfigItem('Cache folder', 'cache')),
        ('results_folder', ConfigItem('Results folder', 'YATSM')),
        ('results_pattern', ConfigItem('Results pattern', 'yatsm_r*')),
        ('mask_band', ConfigItem('Mask band', [8])),
        ('min_values', ConfigItem('Min data values', [0])),
        ('max_values', ConfigItem('Max data values', [10000])),
        ('metadata_file_pattern', ConfigItem('Metadata file pattern',
                                             'L*MTL.txt')),
        ('calc_pheno', ConfigItem('LTM phenology', False)),
    ))

    # Driver controls
    controls_title = 'YATSM Algorithm Options'
    controls = OrderedDict((
        ('calculate_live', ConfigItem('Calculate live', True)),
        ('consecutive', ConfigItem('Consecutive', 5)),
        ('min_obs', ConfigItem('Min obs.', 16)),
        ('threshold', ConfigItem('Threshold', 4.0)),
        ('enable_min_rmse', ConfigItem('Use min RMSE?', True)),
        ('min_rmse', ConfigItem('Min RMSE', 100.0)),
        ('design', ConfigItem('Design', '1 + x + harm(x, 1)')),
        ('test_indices', ConfigItem('Test indices', np.array([2, 3, 4, 5]))),
        ('dynamic_rmse', ConfigItem('Dynamic RMSE', True)),
        ('screen_crit', ConfigItem('Screening crit value', 400.0)),
        ('remove_noise', ConfigItem('Remove noise', True)),
        ('reverse', ConfigItem('Reverse', False)),
        ('regression_type', ConfigItem('Regression type', 'sklearn_Lasso20')),
        ('robust_results', ConfigItem('Robust results', False)),
        ('commit_test', ConfigItem('Commission test', False)),
        ('commit_alpha', ConfigItem('Commission test alpha', 0.10)),
    ))

    def __init__(self, location, config=None):
        super(YATSMTimeSeries, self).__init__(location, config=config)
        # Check for YATSM imports
        if not has_yatsm:
            raise ImportError(has_yatsm_msg)
        if self.config['calc_pheno'].value and not has_yatsm_pheno:
            raise ImportError(has_yatsm_pheno_msg)

        # Find extra metadata
        self._init_metadata()

        # Setup YATSM
        self.yatsm_model = None
        self.X = None
        self.Y = None
        self.coef_name = 'coef'

        # Setup min/max values
        desc, _min_values = self.config['min_values']
        if len(_min_values) == 1:
            _min_values = np.repeat(_min_values, self.series[0].count - 1)
        self.config['min_values'] = ConfigItem(desc, _min_values)

        desc, _max_values = self.config['max_values']
        if len(_max_values) == 1:
            _max_values = np.repeat(_max_values, self.series[0].count - 1)
        self.config['max_values'] = ConfigItem(desc, _max_values)

    def set_custom_controls(self, values):
        logger.debug('Setting custom values')
        for val, attr in zip(values, self.controls):
            desc, current_val = self.controls[attr]
            if isinstance(val, type(current_val)):
                self.controls[attr] = ConfigItem(desc, val)
            else:
                # Make an exception for minimum RMSE since we can pass None
                if attr == 'min_rmse' and isinstance(val, float):
                    self.controls[attr] = ConfigItem(desc, val)
                else:
                    msg = 'Could not set {k} to {v} (current: {c})'.format(
                        k=attr, v=val, c=current_val)
                    raise ValueError(msg)

    def fetch_results(self):
        """ Read or calculate results for current pixel """
        if self.controls['calculate_live'].value:
            self._fetch_results_live()
        else:
            self._fetch_results_saved()

        # Update multitemporal screening metadata
        if self.yatsm_model:
            if (self.controls['calculate_live'] and
                    hasattr(self.yatsm_model, 'X')):
                self.series[0].multitemp_screened = \
                    np.in1d(self.X[:, 1], self.yatsm_model.X[:, 1],
                            invert=True).astype(np.uint8)
            if self.config['calc_pheno'].value:
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
        design = re.sub(r'[\+\-][\ ]+C\(.*\)', '',
                        self.controls['design'].value)
        coef_columns = []
        for k, v in self._design_info.iteritems():
            if not re.match('C\(.*\)', k):
                coef_columns.append(v)
        coef_columns = np.sort(np.asarray(coef_columns))

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
                    index = np.where(self.series[series].images['date'] ==
                                     _bx)[0]
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
            has_dates = all([r in self.yatsm_model.record.dtype.names
                             for r in ('spring_doy', 'autumn_doy')])
            if self.config['calc_pheno'].value and has_dates:
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
        self.yatsm_model = MockResult()
        row, col = self.series[0].py, self.series[0].px

        data_cfg = {
            'output': os.path.join(self.location,
                                   self.config['results_folder'].value),
            'output_prefix': (self.config['results_pattern'].value
                              .replace('*', ''))
        }
        result_filename = get_output_name(data_cfg, row)
        logger.info('Attempting to open: {f}'.format(f=result_filename))

        if not os.path.isfile(result_filename):
            qgis_log('Could not find result for row {r} ({fn})'.format(
                r=row, fn=result_filename))
            return

        z = np.load(result_filename)
        if 'record' not in z.files:
            raise KeyError('Cannot find "record" within saved result ({})'
                           .format(result_filename))
        if 'metadata' not in z.files:
            raise KeyError('Cannot find "metadata" within saved result ({})'
                           .format(result_filename))
        metadata = z['metadata'].item()
        if 'design' not in metadata['YATSM']:
            raise KeyError('Cannot find "design" within saved result metadata '
                           '({})'.format(result_filename))
        self._design_info = metadata['YATSM']['design']

        rec = z['record']
        idx = np.where((rec['px'] == col) & (rec['py'] == row))[0]
        self.yatsm_model.record = rec[idx]

    def _fetch_results_live(self):
        """ Run YATSM and get results """
        logger.debug('Calculating YATSM results on the fly')
        # Setup design matrix, Y, and dates
        self.X = patsy.dmatrix(self.controls['design'].value,
                               {'x': self.series[0].images['ordinal'],
                                'sensor': self.series[0].sensor,
                                'pr': self.series[0].pathrow})
        self._design_info = self.X.design_info.column_name_indexes
        self.Y = self.series[0].data.astype(np.int16)
        self.dates = np.asarray(self.series[0].images['ordinal'])

        mask = self.Y[self.config['mask_band'].value[0] - 1, :]
        Y_data = np.delete(self.Y, self.config['mask_band'].value[0] - 1,
                           axis=0)

        # Mask out masked values
        clear = np.in1d(mask, self.mask_values, invert=True)
        valid = get_valid_mask(Y_data,
                               self.config['min_values'].value,
                               self.config['max_values'].value).astype(np.bool)
        clear *= valid

        # Setup parameters
        estimator = sklearn.linear_model.Lasso(alpha=20)
        reg = self.controls['regression_type'].value
        if hasattr(yatsm.regression, 'packaged'):
            if reg in yatsm.regression.packaged.packaged_regressions:
                reg_fn = yatsm.regression.packaged.find_packaged_regressor(reg)
                try:
                    estimator = jl.load(reg_fn)
                except:
                    logger.error('Cannot load regressor: %s' % reg)
                else:
                    logger.debug('Loaded regressor %s from %s' % (reg, reg_fn))
            else:
                logger.error('Cannot use unknown regression %s' % reg)
        else:
            logger.warning(
                'Using failsafe Lasso(lambda=20) from scikit-learn. '
                'Upgrade to yatsm>=0.5.1 to access more regressors.')

        kwargs = dict(
            estimator=estimator,
            test_indices=self.controls['test_indices'].value,
            consecutive=self.controls['consecutive'].value,
            threshold=self.controls['threshold'].value,
            min_obs=self.controls['min_obs'].value,
            min_rmse=(None if self.controls['enable_min_rmse'].value else
                      self.controls['min_rmse'].value),
            screening_crit=self.controls['screen_crit'].value,
            remove_noise=self.controls['remove_noise'].value,
            dynamic_rmse=self.controls['dynamic_rmse'].value,
        )

        self.yatsm_model = CCDCesque(**version_kwargs(kwargs))
        # Don't want to have DEBUG logging when we run YATSM
        log_level = logger.level
        logger.setLevel(logging.INFO)

        if self.controls['reverse'].value:
            self.yatsm_model.fit(
                np.flipud(self.X[clear, :]),
                np.fliplr(Y_data[:, clear]),
                self.dates[clear][::-1])
        else:
            self.yatsm_model.fit(
                self.X[clear, :],
                Y_data[:, clear],
                self.dates[clear])

        if self.controls['commit_test'].value:
            self.yatsm_model.record = postprocess.commission_test(
                self.yatsm_model, self.controls['commit_alpha'].value)

        # if self.controls['robust_results'].value:
        #     self.coef_name = 'robust_coef'
        #     self.yatsm_model.record = postprocess.refit_record(
        #         self.yatsm_model, 'robust'
        # else:
        #     self.coef_name = 'coef'

        if self.config['calc_pheno'].value:
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
        if self.config['metadata_file_pattern'].value:
            search = find_files(
                self.location, self.config['metadata_file_pattern'].value,
                ignore_dirs=[self.config['results_folder'].value])
            if len(search) == 0:
                logger.error(
                    'Could not find image metadata with pattern {p}'.format(
                        p=self.config['metadata_file_pattern'].value))
            if len(search) != len(self.series[0].images['date']):
                logger.error(
                    'Inconsistent number of metadata files found: '
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
            self.series[0].cloud_cover = np.ones(self.series[0].n) * -9999
            cloud_cover = {}
            for mtl_file in self.mtl_files:
                attrs = parse_landsat_MTL(mtl_file, ['LANDSAT_SCENE_ID',
                                                     'CLOUD_COVER'])
                scene_ID = attrs.get('LANDSAT_SCENE_ID')
                if scene_ID:
                    cloud_cover[scene_ID] = attrs.get('CLOUD_COVER', -9999.0)

            for idx, _id in enumerate(self.series[0].images['id']):
                self.series[0].cloud_cover[idx] = cloud_cover.get(_id, -9999.0)

        if self.config['calc_pheno'].value:
            self.series[0].metadata.append('pheno')
            self.series[0].metadata_names.append('Phenology')
            self.series[0].metadata_table.append(False)
            # Initialize almost all as summer (SUM); first two as SPR/AUT
            self.series[0].pheno = np.repeat('SUM', self.series[0].n)
            self.series[0].pheno[0] = 'SPR'
            self.series[0].pheno[1] = 'AUT'


class MockResult(object):
    record = []
