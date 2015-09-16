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
from ..logger import qgis_log
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

    _px, _py = 0, 0

    def __init__(self, location, config=None):
        super(StackedTimeSeries, self).__init__(location, config=config)

        self.series = [Series({
            'description': 'Stacked Timeseries',
            'symbology_hint_indices': [4, 3, 2],
            'symbology_hint_minmax': [[0, 4000], [0, 5000], [0, 3000]],
            'cache_prefix': 'yatsm_',
            'cache_suffix': '.npy'
        })]

        self._check_cache()

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

        # Read in -- first try from cache
        n_images = sum([s._n_images for s in self.series])
        i = 0
        for s in self.series:
            got_cache = False
            pixel = ts_utils.name_cache_pixel(self._px, self._py,
                                              s.data.shape,
                                              prefix=s.cache_prefix,
                                              suffix=s.cache_suffix)
            pixel_fn = os.path.join(self.location, self._cache_folder, pixel)

            line = ts_utils.name_cache_line(self._py,
                                            s.data.shape,
                                            prefix=s.cache_prefix,
                                            suffix=s.cache_suffix)
            line_fn = os.path.join(self.location, self._cache_folder, line)

            if self._read_cache and os.path.isfile(pixel_fn):
                logger.debug('Trying to read pixel from cache')
                try:
                    dat = ts_utils.read_cache_pixel(pixel_fn, s)
                except:
                    logger.info('Could not read from cache file %s' % pixel_fn)
                    raise
                else:
                    logger.debug('Read pixel from cache')
                    s.data = dat
                    got_cache = True
                    i += s.data.shape[1]
                    yield float(i) / n_images * 100.0
            elif self._read_cache and os.path.isfile(line_fn):
                logger.debug('Trying to read line from cache')
                try:
                    dat = ts_utils.read_cache_line(line_fn, s)
                except:
                    logger.info('Could not read from cache file %s' % line_fn)
                    raise
                else:
                    logger.debug('Read line from cache')
                    s.data = dat[..., self._px]
                    got_cache = True
                    i += s.data.shape[1]
                    yield float(i) / n_images * 100.0
            else:
                logger.info('No cache file here:\n%s\n%s' %
                            (pixel_fn, line_fn))

            if not got_cache:
                for i_img in range(s._n_images):
                    s._scratch_data[:, i_img] = read_pixel_GDAL(
                        s.images['path'][i_img], self._px, self._py)
                    i += 1
                    yield float(i) / n_images * 100.0

                    # Copy from scratch variable if it completes
                    np.copyto(s.data, s._scratch_data)

            if self._write_cache and not got_cache:
                self._write_to_cache(pixel_fn, s)

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
        geom = geo_utils.pixel_geometry(self._geotransform, self._px, self._py)

        return geom.ExportToWkt(), self._spatialref

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
        if not images:
            raise Exception('Could not find any files for "{s}" series'.format(
                s=series.description))

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
            _images[i]['doy'] = int(_images[i]['date'].strftime('%j'))

        # Sort by date
        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]

        series.images = _images.copy()

    def _init_attributes(self, series):
        # Determine geotransform and projection
        self._geotransform = None
        self._spatialref = None

        ds = None
        for fname in series.images['path']:
            try:
                ds = gdal.Open(fname, gdal.GA_ReadOnly)
            except:
                pass
            else:
                break
        if ds is None:
            raise Exception(
                'Could not initialize attributes for {s} series'.format(
                    s=series.description))

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

    def _write_to_cache(self, filename, series):
        """ TOOD
        """
        try:
            ts_utils.write_cache_pixel(filename, series)
        except Exception as e:
            # TODO
            qgis_log('Could not cache pixel to {f}: {e}'.format(
                f=filename, e=e.message), level=logging.ERROR)

    def _read_from_cache(self):
        """ TODO
        """
        pass
