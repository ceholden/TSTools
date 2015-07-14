""" A driver for running YATSM on stacked Landsat/PALSAR timeseries
"""
from datetime import datetime as dt
import logging
import os

import numpy as np
import patsy

from . import timeseries_yatsm
from .timeseries import Series
from .ts_utils import find_files, parse_landsat_MTL

logger = logging.getLogger('tstools')


class YATSMLandsatPALSARTS(timeseries_yatsm.YATSMTimeSeries):

    """ Timeseries driver for Timeseries of Landsat/PALSAR timeseries
    """
    description = 'Landsat/PALSAR YATSM'
    location = None
    mask_values = np.array([2, 3, 4, 255])

    # Driver configuration
    _stack_pattern = 'L*stack'
    _date_format = '%Y%j'
    _date_index = [9, 16]
    _ps_dir = 'RADAR'
    _ps_stack_pattern = '*ALPSRP*'
    _ps_date_format = '%Y%m%d'
    _ps_date_index = [8, 16]
    _cache_folder = 'cache_fusion'
    _results_folder = 'YATSM'
    _results_pattern = 'yatsm_r*'
    _mask_band = [8, 0, 0]
    _min_values = [0]
    _max_values = [10000]
    _metadata_file_pattern = 'L*MTL.txt'

    config = [
        '_stack_pattern',
        '_date_index',
        # '_date_format',
        '_ps_dir',
        '_ps_stack_pattern',
        # '_ps_date_format',
        '_ps_date_index',
        '_cache_folder',
        '_results_folder',
        '_results_pattern',
        '_mask_band',
        '_min_values', '_max_values',
        '_metadata_file_pattern']
    config_names = [
        'Landsat stack pattern',
        'Landsat date index',
        # 'Landsat date format'
        'PALSAR data directory',
        'PALSAR stack pattern',
        # 'PALSAR date format'
        'PALSAR date index',
        'Cache folder',
        'Results folder',
        'Results pattern',
        'Mask band',
        'Min data values', 'Max data values',
        'Metadata file pattern']

    def __init__(self, location, config=None):
        super(YATSMLandsatPALSARTS, self).__init__(location, config=config)

        # Change name of first series
        self.series[0].description = 'Landsat Timeseries'

        # Add series for RADAR HH/HV/ratio
        self.series.append(Series({
            'description': 'PALSAR HH Timeseries',
            'symbology_hint_indices': [0],
            'symbology_hint_minmax': [0, 255]
        }))
        self.series.append(Series({
            'description': 'PALSAR HH/HV/Ratio Timeseries',
            'symbology_hint_indices': [0, 1, 2],
            'symbology_hint_minmax': [0, 255]
        }))

        self._find_radar()

    def _find_radar(self):
        """ Find RADAR images and initialize series
        """
        location = os.path.join(self.location, self._ps_dir)

        # Ignore results folder and cache, if we have it
        ignore_dirs = []
        if hasattr(self, '_cache_folder'):
            ignore_dirs.append(getattr(self, '_cache_folder'))
        if hasattr(self, '_results_folder'):
            ignore_dirs.append(getattr(self, '_results_folder'))

        # Find HH images
        hh_images = find_files(location, self._ps_stack_pattern + '*hh.gtif',
                               ignore_dirs=ignore_dirs)
        if not hh_images:
            raise Exception('Could not find any files for "{s}" series'.format(
                s=self.series[1].description))
        self.series[1]._n_images = len(hh_images)
        self.series[1]._n_band = 1

        # Find HH/HV/Ratio VRT images
        vrt_images = find_files(location, self._ps_stack_pattern + '*.vrt',
                                ignore_dirs=ignore_dirs)
        if not vrt_images:
            raise Exception('Could not find any files for "{s}" series'.format(
                s=self.series[2].description))
        self.series[2]._n_images = len(vrt_images)
        self.series[2]._n_band = 3

        # Initialize image attributes
        _images = np.empty(len(hh_images), dtype=self.series[1].images.dtype)
        for i, img in enumerate(hh_images):
            _images[i]['filename'] = os.path.basename(img)
            _images[i]['path'] = img
            _images[i]['id'] = os.path.basename(os.path.dirname(img))
            _images[i]['date'] = dt.strptime(
                _images[i]['filename'][
                    self._ps_date_index[0]:self._ps_date_index[1]],
                self._ps_date_format)
            _images[i]['ordinal'] = dt.toordinal(_images[i]['date'])
            _images[i]['doy'] = int(_images[i]['date'].strftime('%j'))

        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]
        self.series[1].images = _images.copy()

        _images = np.empty(len(vrt_images), dtype=self.series[1].images.dtype)
        for i, img in enumerate(vrt_images):
            _images[i]['filename'] = os.path.basename(img)
            _images[i]['path'] = img
            _images[i]['id'] = os.path.basename(os.path.dirname(img))
            _images[i]['date'] = dt.strptime(
                _images[i]['filename'][
                    self._ps_date_index[0]:self._ps_date_index[1]],
                self._ps_date_format)
            _images[i]['ordinal'] = dt.toordinal(_images[i]['date'])
            _images[i]['doy'] = int(_images[i]['date'].strftime('%j'))

        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]
        self.series[2].images = _images.copy()

        # Initialize remaining attributes
        self.series[1].band_names = ['HH']
        self.series[2].band_names = ['HH', 'HV', 'HH/HV Ratio']
        for series in self.series[1:]:
            series.data = np.zeros(
                (series._n_band, series._n_images),
                dtype=np.int16)
            series._scratch_data = np.zeros(
                (series._n_band, series._n_images),
                dtype=np.int16)
            series.mask = np.ones(series._n_images, dtype=np.bool)
