""" Timeseries driver for a simple 'stacked' timeseries dataset
"""
try:
    range = xrange
except:
    pass

from datetime import datetime as dt
import logging
import os

import numpy as np
from osgeo import gdal, gdal_array

from . import ts_utils
from .reader import read_pixel_GDAL
from .timeseries import AbstractTimeSeriesDriver, Series
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
    _mask_band = 8

    config = ['_stack_pattern',
              '_date_index',
              '_date_format',
              '_mask_band']
    config_names = ['Stack pattern',
                    'Index of date in ID',
                    'Date format',
                    'Mask band']

    _px, _py = 0, 0

    def __init__(self, location, config=None):
        super(StackedTimeSeries, self).__init__(location, config=config)

        self.series = [Series({'description': 'Stacked Timeseries'})]

        for series in self.series:
            self._init_images(series)
            self._init_attributes(series)

            series.data = np.zeros((series._n_band, series._n_images),
                                   dtype=series._dtype)
            series._scratch_data = np.zeros_like(series.data)
            series.mask = np.ones(series._n_images, dtype=np.bool)

    @property
    def pixel_pos(self):
        return self._pixel_pos

    def _update_pixel_pos(self):
        self._pixel_pos = 'Row {py}/Column {px}'.format(py=self._py,
                                                        px=self._px)

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
        # Convert coordinate reference system
        mx, my = geo_utils.reproject_point(mx, my, crs_wkt, self._spatialref)

        # Convert map coordinates into image
        self._px, self._py = geo_utils.point2pixel(mx, my, self._geotransform)
        self._update_pixel_pos()

        if (self._px < 0 or self._py < 0 or
                self._px > self._x_size or self._py > self._y_size):
            logger.error('Coordinate specified is outside of dataset '
                         '(px/py: {px}/{py})'.format(px=self._px, py=self._py))
            raise IndexError('Coordinate specified is outside of dataset')

        i = 0
        n_images = sum([s._n_images for s in self.series])
        for series in self.series:
            for i_img in range(series._n_images):
                series._scratch_data[:, i_img] = read_pixel_GDAL(
                    series.images['path'], self._px, self._py, i_img)
                i += 1
                yield float(i) / n_images * 100.0

        # Copy from scratch variable if it completes
        np.copyto(series.data, series._scratch_data)

        # Update mask
        for series in self.series:
            series.mask = np.in1d(series.data[self._mask_band - 1, :],
                                  self.mask_values, invert=True)

    def fetch_results(self):
        """ Read or calculate results for current pixel """
        pass

    def get_data(self, series, band, mask=True):
        """ Return data for a given band

        Args:
          series (int): index of Series containing data
          band (int): index of band to return
          mask (bool, optional): return data masked or left unmasked, if
            supported by driver implementation

        Returns:
          tuple: two 1D NumPy arrays containing dates (x) and data (y)

        """

        x = self.series[series].images['date']
        y = self.series[series].data[band, :]

        if mask:
            x = x[self.series[series].mask]
            y = y[self.series[series].mask]

        return x, y

    def get_prediction(self, series, band):
        pass

    def get_breaks(self, series, band):
        pass

    def _init_images(self, series):
        """ Sets up `self.images` by finding and describing imagery """
        # Ignore results folder and cache, if we have it
        ignore_dirs = []
        if hasattr(self, '_cache_folder'):
            ignore_dirs.append(getattr(self, '_cache_folder'))
        if hasattr(self, '_results_folder'):
            ignore_dirs.append(getattr(self, '_results_folder'))

        # Find images
        images = ts_utils.find_files(self.location, self._stack_pattern,
                                     ignore_dirs=ignore_dirs)

        # Extract attributes
        _images = np.empty(len(images), dtype=series.images.dtype)
        series._n_images = len(images)

        for i, img in enumerate(images):
            _images[i]['filename'] = os.path.basename(img)
            _images[i]['path'] = img
            _images[i]['id'] = os.path.basename(os.path.dirname(img))
            _images[i]['date'] = dt.strptime(
                _images[i]['id'][self._date_index[0]:self._date_index[1]],
                self._date_format)
            _images[i]['ordinal'] = dt.toordinal(_images[i]['date'])

        # Sort by date
        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]

        series.images = _images.copy()

    def _init_attributes(self, series):
        # Determine geotransform and projection
        self._geotransform = None
        self._spatialref = None

        for fname in series.images['path']:
            try:
                ds = gdal.Open(fname, gdal.GA_ReadOnly)
            except:
                pass
            break

        self._x_size = ds.RasterXSize
        self._y_size = ds.RasterYSize
        series._n_band = ds.RasterCount
        series._dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
            ds.GetRasterBand(1).DataType)

        _band_names = []
        for i_b in range(ds.RasterCount):
            name = ds.GetRasterBand(i_b + 1).GetDescription()
            if not name:
                name = 'Band {b}'.format(b=i_b + 1)
            _band_names.append(name)
        series.band_names = list(_band_names)

        self._geotransform = ds.GetGeoTransform()
        self._spatialref = ds.GetProjection()

        ds = None
