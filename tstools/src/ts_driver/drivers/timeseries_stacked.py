""" Timeseries driver for a simple 'stacked' timeseries dataset
"""
from collections import OrderedDict
import logging
import os

import numpy as np

from ..ts_utils import find_files, ConfigItem
from ..series import Series
from ..timeseries import AbstractTimeSeriesDriver
from ...utils import geo_utils

logger = logging.getLogger('tstools')


class StackedTimeSeries(AbstractTimeSeriesDriver):
    """ Simple 'stacked' timeseries driver

    'Layer Stacked' timeseries contain all the same bands and are of uniform
    geographic extent and size. For an example of a "stacked" dataset, visit

    https://github.com/ceholden/landsat_stack

    This timeseries driver has only one Series that does not have extra
    metadata.
    """
    description = 'Layer Stacked Timeseries'
    location = None
    series = []
    mask_values = np.array([2, 3, 4, 255])
    _pixel_pos = ''
    has_results = False

    # Driver configuration
    config = OrderedDict((
        ('stack_pattern', ConfigItem('Stack pattern', 'L*stack')),
        ('date_index', ConfigItem('Index of date in ID', [9, 16])),
        ('date_format', ConfigItem('Date format', '%Y%j')),
        ('cache_folder', ConfigItem('Cache folder', 'cache')),
        ('mask_band', ConfigItem('Mask band', [8])),
    ))

    _read_cache, _write_cache = False, False

    def __init__(self, location, config=None):
        super(StackedTimeSeries, self).__init__(location, config=config)

        # Find images and init Series
        ignore_dirs = []
        if 'cache_folder' in self.config:
            ignore_dirs.append(self.config['cache_folder'].value)
        if 'results_folder' in self.config:
            ignore_dirs.append(self.config['results_folder'].value)
        images = find_files(self.location,
                            self.config['stack_pattern'].value,
                            ignore_dirs=ignore_dirs)

        self.series = [
            Series(
                images,
                self.config['date_index'].value,
                self.config['date_format'].value,
                {
                    'description': 'Stacked TS',
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
        cache_folder = os.path.join(self.location,
                                    self.config['cache_folder'].value)

        i = 0
        n = sum([len(series.images) for series in self.series])

        descs, rowcol = [], []
        for j, series in enumerate(self.series):
            _mx, _my = geo_utils.reproject_point(mx, my, crs_wkt, series.crs)
            _px, _py = geo_utils.point2pixel(_mx, _my, series.gt)

            descs.append(series.description)
            rowcol.append('%i/%i' % (_py, _px))

            for _i in series.fetch_data(mx, my, crs_wkt,
                                        cache_folder=cache_folder,
                                        read_cache=self._read_cache,
                                        write_cache=self._write_cache):
                i += 1
                yield i / float(n) * 100.0

        # Collapse pixel position if same row/column
        pos = []
        for u_rowcol in set(rowcol):
            entry = []
            for _desc, _rowcol in zip(descs, rowcol):
                if _rowcol == u_rowcol:
                    entry.append(_desc)
            pos.append('/'.join(entry) + ' - ' + u_rowcol)

        self._pixel_pos = 'Row/Col: ' + '; '.join(pos)

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

        for mask_band, series in zip(self.config['mask_band'].value,
                                     self.series):
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
        self.cache_folder = os.path.join(self.location,
                                         self.config['cache_folder'].value)
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
