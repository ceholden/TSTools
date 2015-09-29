""" Timeseries driver for a simple 'stacked' timeseries dataset
"""
import logging
import os

import numpy as np

from . import ts_utils
from .series import Series
from .timeseries import AbstractTimeSeriesDriver
from ..utils import geo_utils

logger = logging.getLogger('tstools')


class StackedTimeSeries(AbstractTimeSeriesDriver):
    """ Simple 'stacked' timeseries driver

    'Layer Stacked' timeseries contain all the same bands and are of uniform
    geographic extent and size. This timeseries driver has only one Series that
    does not have extra metadata and

    """
    description = 'Layer Stacked Timeseries'
    location = None
    series = []
    mask_values = np.array([2, 3, 4, 255])
    _pixel_pos = ''
    has_results = False

    # Driver configuration
    _stack_pattern = 'L*stack'
    _date_index = [9, 16]
    _date_format = '%Y%j'
    _cache_folder = 'cache'
    _mask_band = [8]

    config = ['_stack_pattern',
              '_date_index',
              '_date_format',
              '_cache_folder',
              '_mask_band']
    config_names = ['Stack pattern',
                    'Index of date in ID',
                    'Date format',
                    'Cache folder',
                    'Mask band']

    _read_cache, _write_cache = False, False

    def __init__(self, location, config=None):
        super(StackedTimeSeries, self).__init__(location, config=config)

        # Find images and init Series
        ignore_dirs = []
        if hasattr(self, '_cache_folder'):
            ignore_dirs.append(self._cache_folder)
        if hasattr(self, '_results_folder'):
            ignore_dirs.append(self._results_folder)
        images = ts_utils.find_files(self.location, self._stack_pattern,
                                     ignore_dirs=ignore_dirs)

        self.series = [
            Series(images, {
                'description': 'Stacked Timeseries',
                'symbology_hint_indices': [4, 3, 2],
                'symbology_hint_minmax': [[0, 4000], [0, 5000], [0, 3000]],
                'cache_prefix': 'yatsm_',
                'cache_suffix': '.npy'
            })
        ]
        self._check_cache()

    @property
    def pixel_pos(self):
        return self._pixel_pos

    def fetch_data(self, mx, my, crs_wkt):
        """ Read data for a given x, y coordinate in a given CRS

        Args:
          mx (float): map X location
          my (float): map Y location
          crs_wkt (str): Well Known Text (Wkt) Coordinate reference system
            string describing (x, y)

        Yields:
          float: current retrieval progress (0 to 1)

        Raises:
          IndexError: raise IndexError if map coordinates are outside of
            dataset

        """
        cache_folder = os.path.join(self.location, self._cache_folder)

        i = 0
        n = sum([len(series.images) for series in self.series])

        pos = []
        for i, series in enumerate(self.series):
            _mx, _my = geo_utils.reproject_point(mx, my, crs_wkt, series.crs)
            _px, _py = geo_utils.point2pixel(_mx, _my, series.gt)
            pos.append('Series %i - %i/%i' % (i + 1, _py, _px))

            for _i in series.fetch_data(mx, my, crs_wkt,
                                        cache_folder=cache_folder,
                                        read_cache=self._read_cache,
                                        write_cache=self._write_cache):
                i += _i
                yield i / float(n) * 100.0

        self._pixel_pos = 'Row/Column: ' + '; '.join(pos)

        # Update mask
        self.update_mask()

    def fetch_results(self):
        """ Read or calculate results for current pixel """
        pass

    def update_mask(self, mask_values=None):
        """ Update data mask. Optionally also update mask values

        Args:
          mask_values (iterable, optional): values to mask

        """
        if mask_values is not None:
            self.mask_values = np.asarray(mask_values).copy()

        for mask_band, series in zip(self._mask_band, self.series):
            if not mask_band:
                continue
            series.mask = np.in1d(series.data[mask_band - 1, :],
                                  self.mask_values, invert=True)

    def get_data(self, series, band, mask=True, indices=None):
        """ Return data for a given band

        Args:
          series (int): index of Series containing data
          band (int or np.ndarray): index of band (int) or indices of bands
            (np.ndarray) to return
          mask (bool, optional): return data masked or left unmasked, if
            supported by driver implementation
          indices (None or np.ndarray, optional): np.ndarray indices to subset
            data in conjunction with mask, if needed, or None for no indexing

        Returns:
          tuple: two NumPy arrays containing images (X) and data (y)

        """
        X = self.series[series].images
        # y = self.series[series].data[band, :]
        y = self.series[series].data.take(band, axis=0)

        if mask is True:
            mask = self.series[series].mask
        if isinstance(indices, np.ndarray):
            if isinstance(mask, np.ndarray):
                mask = indices[np.in1d(indices,
                                       np.where(self.series[series].mask)[0])]
            else:
                mask = indices
        elif isinstance(mask, np.ndarray):
            mask = np.where(mask)[0]

        if mask is not False:
            X = X.take(mask, axis=0)
            y = y.take(mask, axis=0)

        return X, y

    def get_prediction(self, series, band):
        pass

    def get_breaks(self, series, band):
        pass

    def get_residuals(self, series, band):
        pass

    def get_geometry(self):
        """ Return geometry and projection for data queried

        Returns:
          tuple: geometry and projection of data queried formatted as
            Well Known Text (Wkt)

        """
        geom_wkts, crss = [], []
        for series in self.series:
            _geom_wkt, _crs = series.get_geometry()
            geom_wkts.append(_geom_wkt)
            crss.append(_crs)

        if len(geom_wkts) > 1:
            geom, crs = geo_utils.merge_geometries(geom_wkts, crss)
            geom = geom.ExportToWkt()
        else:
            geom, crs = geom_wkts[0], crss[0]

        return geom, crs

    def _check_cache(self):
        """ Check for read/write from/to cache folder
        """
        self.cache_folder = os.path.join(self.location, self._cache_folder)
        if (os.path.exists(self.cache_folder) and
                os.path.isdir(self.cache_folder)):
            if os.access(self.cache_folder, os.R_OK):
                self._read_cache = True

            if os.access(self.cache_folder, os.W_OK):
                self._write_cache = True
        else:
            try:
                os.mkdir(self.cache_folder)
            except:
                pass
            else:
                self._read_cache, self._write_cache = True, True

        logger.debug('Cache read/write: {r}/{w}'.format(
            r=self._read_cache, w=self._write_cache))
