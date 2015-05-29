""" Timeseries driver for a simple 'stacked' timeseries dataset
"""
try:
    range = xrange
except:
    pass

from datetime import datetime as dt
import fnmatch
import logging
import os

import numpy as np
from osgeo import gdal, gdal_array, osr

from . import utils
from .reader import read_pixel_GDAL
from .timeseries import AbstractTimeSeries
from ..utils import geo_utils


class StackedTimeSeries(AbstractTimeSeries):
    """ Simple 'stacked' timeseries driver

    'Layer Stacked' timeseries contain all the same bands and are of uniform
    geographic extent and size. This timeseries driver does not have results.

    """
    description = 'Layer Stacked Timeseries'
    location = None
    images = np.empty(0,
                      dtype=[('filename', object),
                             ('path', object),
                             ('id', object),
                             ('date', object),
                             ('ordinal', 'u4')])
    band_names = None
    mask_values = np.array([2, 3, 4, 255])
    _pixel_pos = ''

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

    def __init__(self, location, config=None):
        super(StackedTimeSeries, self).__init__(location, config=config)

        self._init_images()
        self._init_attributes()

        self._data = np.zeros((self._n_band, self._n_images),
                              dtype=self._dtype)
        self._mask = np.ones(self._n_images, dtype=np.bool)

    @property
    def pixel_pos(self):
        return self._pixel_pos

    def fetch_data(self, mx, my, crs):
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
        # Convert coordinate
        px, py = geo_utils.point2pixel(mx, my, crs)

        if px < 0 or py < 0 or px > self._x_size or py > self._y_size:
            raise IndexError('Coordinate specified is outside of dataset')

        # TODO: refactor into _fetch_data_images and _fetch_data_cache
        for i in range(self._n_images):
            self._data[:, i] = read_pixel_GDAL(self.images['filename'],
                                               px, py, i)
            yield float(i) / self._n_images

        return 1

    def fetch_results(self):
        pass

    def get_data(self, band, mask=True):
        if mask:
            return self._data[band, self._mask]
        else:
            return self._data[band, :]

    def get_prediction(self, band):
        pass

    def get_breaks(self, band):
        pass

    def _init_images(self):
        """ Sets up `self.images` by finding and describing imagery """
        # Ignore results folder and cache, if we have it
        ignore_dirs = []
        if hasattr(self, '_cache_folder'):
            ignore_dirs.append(getattr(self, '_cache_folder'))
        if hasattr(self, '_results_folder'):
            ignore_dirs.append(getattr(self, '_results_folder'))

        # Find images
        images = utils.find_files(self.location, self._stack_pattern,
                                  ignore_dirs=ignore_dirs)

        # Extract attributes
        self.images = np.empty(len(images), dtype=self.images.dtype)

        for i, img in enumerate(images):
            self.images[i]['filename'] = os.path.basename(img)
            self.images[i]['path'] = img
            self.images[i]['id'] = os.path.basename(os.path.dirname(img))
            self.images[i]['date'] = dt.strptime(
                self.images[i]['id'][self._date_index[0]:self._date_index[1]],
                self._date_format)
            self.images[i]['ordinal'] = dt.toordinal(self.images[i]['date'])

        self._n_images = len(images)

    def _init_attributes(self):
        # Determine geotransform and projection
        self._geotransform = None
        self._spatialref = None

        for fname in self.images['path']:
            try:
                ds = gdal.Open(fname, gdal.GA_ReadOnly)
            except:
                pass
            break

        self._x_size = ds.RasterXSize
        self._y_size = ds.RasterYSize
        self._n_band = ds.RasterCount
        self._dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
            ds.GetRasterBand(1).DataType)

        self.band_names = []
        for i_b in range(ds.RasterCount):
            name = ds.GetRasterBand(i_b + 1).GetDescription()
            if not name:
                name = 'Band {b}'.format(b=i_b + 1)
            self.band_names.append(name)

        self._geotransform = ds.GetGeoTransform()
        self._spatialref = osr.SpatialReference(ds.GetProjection())

        ds = None
