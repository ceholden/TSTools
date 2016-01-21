""" Module for Series dataset container classes
"""
from datetime import datetime as dt
import logging
import os

import numpy as np
from osgeo import gdal, gdal_array

from . import ts_utils
from .reader import read_pixel_GDAL
from ..utils import geo_utils

logger = logging.getLogger('tstools')


class Series(object):
    """ A container class for timeseries driven by a TimeSeries driver

    Note:
      You can set class attributes using an optionally supplied configuration
        dictionary when instantiating the class.

    Args:
        filenames (list): filenames for images to be included in the Series
        date_index (tuple): start and end index of an image filename or ID
            that contains the image's date
        date_format (str): format of date in an image's filename or ID

    Attributes:
        description (str): description of timeseries series
        images (np.ndarray): NumPy structured array containing attributes for
            all timeseries images. Structured array columns must include
            "filename" (str), "path" (str), "id" (str), "date" (dt.Date), and
            "ordinal" (int).
        band_names (iterable): list of names describing each band

        symbology_hint_indices (tuple): three band indices (RGB) used for
            default symbology
        symbology_hint_minmax (iterable): one or more pairs of integers used as
            the minimum and maximum scaling for default image symbology

        metadata (iterable): list of variables used for plot and image table
            metadata
        metadata_table (iterable): list of True/False for each metadata
            variable indicating suitability of variable within images table on
            "Controls" tab
        metadata_names (iterable): list of names of variables used for plot and
            image table metadata

        cache_prefix (str): cache filename prefix
        cache_suffix (str): cache filename suffix

    Methods:
        fetch_data: read data for a given X/Y, yielding progress as percentage
        get_geometry: return Well Known Text (Wkt) of geometry and projection
            of query specified by X/Y coordinate

    """
    description = 'Stacked TimeSeries'
    images = np.empty(0,
                      dtype=[('filename', object),
                             ('path', object),
                             ('id', object),
                             ('date', object),
                             ('ordinal', 'u4'),
                             ('doy', 'u2')])
    band_names = []

    # Basic symbology hints by default
    symbology_hint_indices = [3, 2, 1]
    # Specify two numbers (int or float) for one min/max for all bands
    # OR specify np.ndarray for each band in dataset for min and max
    #     e.g. symbology_hint_minmax = [np.zeros(8), np.ones(8) * 10000]
    symbology_hint_minmax = [0, 10000]

    metadata = []
    metadata_table = []
    metadata_names = []

    cache_prefix = ''
    cache_suffix = ''

    px, py = 0, 0

    def __init__(self, filenames, date_index=(9, 16), date_format='%Y%j',
                 config=None):
        self._init_images(filenames, date_index, date_format)
        self.data = np.zeros((self.count, self.n), dtype=np.float)
        self._scratch_data = np.zeros_like(self.data)
        self.mask = np.ones(self.n, dtype=np.bool)

        if config:
            self.__dict__.update(config)

    def fetch_data(self, mx, my, crs_wkt,
                   cache_folder='',
                   read_cache=False, write_cache=False):
        """ Read data for a given x, y coordinate in a given CRS

        Args:
            mx (float): map X location
            my (float): map Y location
            crs_wkt (str): Well Known Text (Wkt) Coordinate reference system
                string describing (x, y)
            cache_folder (str): path to cache folder
            read_cache (bool): allow reading from cache
            write_cache (bool): allow writing to cache

        Yields:
            float: current retrieval progress (1 to n)

        Raises:
            IndexError: raise IndexError if map coordinates are outside of
                dataset

        """
        mx, my = geo_utils.reproject_point(mx, my, crs_wkt, self.crs)
        self.px, self.py = geo_utils.point2pixel(mx, my, self.gt)

        if (self.px < 0 or self.py < 0 or
                self.px > self.width or self.py > self.height):
            raise IndexError('Coordinate specific outside of dataset: '
                             '%i/%i' % (self.px, self.py))

        got_cache = False
        pixel = ts_utils.name_cache_pixel(self.px, self.py,
                                          self.data.shape,
                                          prefix=self.cache_prefix,
                                          suffix=self.cache_suffix)
        pixel_fn = os.path.join(cache_folder, pixel)

        line = ts_utils.name_cache_line(self.py,
                                        self.data.shape,
                                        prefix=self.cache_prefix,
                                        suffix=self.cache_suffix)
        line_fn = os.path.join(cache_folder, line)

        i = 0
        # First try pixel cache
        if read_cache and os.path.isfile(pixel_fn):
            logger.debug('Trying to read pixel from cache')
            try:
                dat = ts_utils.read_cache_pixel(pixel_fn, self)
            except Exception as e:
                logger.warning('Could not read from cache file %s: %s' %
                               (pixel_fn, e.message))
            else:
                logger.debug('Read pixel from cache')
                self.data = dat
                got_cache = True
                i += self.data.shape[1]
                yield float(i)

        # If pixel cache fails, try line
        if read_cache and os.path.isfile(line_fn) and not got_cache:
            logger.debug('Trying to read line from cache')
            try:
                dat = ts_utils.read_cache_line(line_fn, self)
            except Exception as e:
                logger.warning('Could not read from cache file %s: %s' %
                               (line_fn, e.message))
            else:
                logger.debug('Read line from cache')
                self.data = dat[..., self.px]
                got_cache = True
                i += self.data.shape[1]
                yield float(i)

        # Last resort -- read from images
        if not got_cache:
            for i_img in range(self.n):
                self._scratch_data[:, i_img] = read_pixel_GDAL(
                    self.images['path'][i_img], self.px, self.py)
                i += 1
                yield float(i)

                # Copy from scratch variable if it completes
                np.copyto(self.data, self._scratch_data)

        if write_cache and not got_cache:
            try:
                ts_utils.write_cache_pixel(pixel_fn, self)
            except Exception as e:
                logger.warning('Could not cache pixel to %s: %s' %
                               (pixel_fn, e.message))

    def get_geometry(self):
        """ Return geometry and projection for data queried

        Returns:
            tuple: geometry and projection of data queried formatted as
                Well Known Text (Wkt)

        """
        geom = geo_utils.pixel_geometry(self.gt, self.px, self.py)

        return geom.ExportToWkt(), self.crs

    def _init_images(self, images, date_index=[9, 16], date_format='%Y%j'):
        n = len(images)
        if n == 0:
            raise Exception('Cannot initialize a Series of 0 images')
        else:
            self.n = n
            logger.debug('Trying to initialize a Series of %i images' % self.n)

        # Extract images information
        _images = np.empty(self.n, dtype=self.images.dtype)

        for i, img in enumerate(images):
            _images[i]['filename'] = os.path.basename(img)
            _images[i]['path'] = img
            _images[i]['id'] = os.path.basename(os.path.dirname(img))

            try:
                date = _images[i]['id'][date_index[0]:date_index[1]]
                date = dt.strptime(date, date_format)
            except:
                try:
                    date = _images[i]['filename'][date_index[0]:date_index[1]]
                    date = dt.strptime(date, date_format)
                except:
                    raise Exception(
                        'Could not parse date from ID or filename '
                        '(date index=%s:%s, format=%s)\n%s\n%s' %
                        (date_index[0], date_index[1], date_format,
                         _images[i]['id'], _images[i]['filename'])
                    )
            _images[i]['date'] = date
            _images[i]['ordinal'] = dt.toordinal(_images[i]['date'])
            _images[i]['doy'] = int(_images[i]['date'].strftime('%j'))

        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]

        self.images = _images.copy()

        # Extract attributes
        self.gt = None
        self.crs = None
        ds = None
        for fname in images:
            try:
                ds = gdal.Open(fname, gdal.GA_ReadOnly)
            except:
                pass
            else:
                break
        if ds is None:
            raise Exception('Could not initialize attributes for %s series: '
                            'could not open any images in Series with GDAL' %
                            self.description)

        self.band_names = []
        for i_b in range(ds.RasterCount):
            name = ds.GetRasterBand(i_b + 1).GetDescription()
            if not name:
                name = 'Band %s' % str(i_b + 1)
            self.band_names.append(name)

        self.width = ds.RasterXSize
        self.height = ds.RasterYSize
        self.count = ds.RasterCount
        self.dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
            ds.GetRasterBand(1).DataType)
        self.gt = ds.GetGeoTransform()
        self.crs = ds.GetProjection()
