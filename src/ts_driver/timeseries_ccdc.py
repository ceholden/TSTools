# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCTimeSeries
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@bu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import datetime as dt
import fnmatch
import logging
import os
import sys

import numpy as np
import scipy.io
try:
    from osgeo import gdal
except:
    import gdal

import timeseries
from timeseries import mat2dict, ImageReader
import utils

logger = logging.getLogger('tstools')


class CCDCTimeSeries(timeseries.AbstractTimeSeries):
    """Class holding data and methods for time series used by CCDC
    (Change Detection and Classification). Useful for QGIS plugin 'TSTools'.

    More doc TODO
    """

    # description name for TSTools data model plugin loader
    description = 'CCDC Time Series'

    # TODO add some container for "metadata" that can be used in table
    #      (hint: metadata)
    image_names = []
    filenames = []
    filepaths = []
    length = 0
    dates = np.array([])
    n_band = 0
    _data = np.array([])
    _tmp_data = np.array([])
    result = []

    has_results = False
    read_cache = False
    write_cache = False

    x_size = 0
    y_size = 0
    geo_transform = None
    projection = None
    fformat = None
    datatype = None
    band_names = []
    readers = []

    _px = None
    _py = None

    mask_val = [2, 3, 4, 255]

    image_pattern = 'L*'
    stack_pattern = '*stack'
    results_folder = 'TSFitMap'
    results_pattern = 'record_change*'
    cache_folder = '.cache'
    mask_band = 8
    days_in_year = 365.25

    configurable = ['image_pattern', 'stack_pattern',
                    'results_folder', 'results_pattern',
                    'cache_folder', 'mask_band',
                    'days_in_year']
    configurable_str = ['Image folder pattern', 'Stack Pattern',
                        'Results folder', 'Results pattern',
                        'Cache folder pattern', 'Mask band',
                        'Days in Year']

    sensor = np.array([])
    pathrow = np.array([])

    metadata = ['sensor', 'pathrow']
    metadata_str = ['Sensor', 'Path/Row']

    def __init__(self, location, config=None):
        if config:
            self.set_custom_config(config)

        super(CCDCTimeSeries, self).__init__(location,
                                             self.image_pattern,
                                             self.stack_pattern)

        self._find_stacks()
        self._get_attributes()
        self._get_dates()

        if getattr(self, 'results_folder', None) is not None:
            self._check_results()

        if getattr(self, 'cache_folder', None) is not None:
            self.read_cache, self.write_cache = utils.check_cache(
                os.path.join(self.location, self.cache_folder))
        logger.info('Can read from cache?: {b}'.format(b=self.read_cache))
        logger.info('Can write to cache?: {b}'.format(b=self.write_cache))

        self._open_ts()

        self._data = np.zeros([self.n_band, self.length], dtype=self.datatype)

        # Retrieve metadata
        self._get_metadata()

    def set_custom_config(self, values):
        """ Set custom configuration options

        Arguments:
            values          list of values matched to self.configurable

        """
        logger.debug('Setting custom values')
        logger.debug(values)
        logger.debug(self.configurable)

        for v, k in zip(values, self.configurable):
            # Lookup current value for configurable item
            current_value = getattr(self, k, None)

            logger.debug('    {k} : {cv} <-- {v} ({t})'.format(
                k=k,
                v=v,
                cv=current_value,
                t=type(v)
            ))

            # Make sure new value is of same type
            if isinstance(v, type(current_value)):
                # Set attribute
                setattr(self, k, v)
            else:
                raise AttributeError(
                    'Cannot set value {v} for {o} (current value {cv})'.
                    format(v=v, o=k, cv=current_value))

    def get_ts_pixel(self, use_cache=True, do_cache=True):
        """ Fetch pixel data for the current pixel and set to self._data

        Uses:
            self._px, self._py

        Args:
            use_cache               allow for retrieval of data from cache
            do_cache                enable caching of retrieved results

        """
        read_data = False

        if self.read_cache and use_cache is True:
            read_data = self.retrieve_from_cache()

        if read_data is False:
            # Read in from images
            for i in xrange(self.length):
                self.retrieve_pixel(i)

        # Apply mask
        self.apply_mask()

        # Try to cache result if we didn't just read it from cache
        if self.write_cache and do_cache and not read_data:
            try:
                self.write_to_cache()
            except:
                logger.error('Could not write to cache file')
                raise

    def retrieve_pixel(self, index):
        """ Retrieve pixel data for a given x/y and index in time series

        Uses:
            self._px, self._py

        Args:
            index                   index of image in time series

        """
        if self._tmp_data.shape[0] == 0:
            self._tmp_data = np.zeros_like(self._data)

        # Read in from images
        self._tmp_data[:, index] = self.readers[index].get_pixel(
            self._py, self._px)
        self._data[:, index] = self.readers[index].get_pixel(
            self._py, self._px)

        if index == self.length - 1:
            print 'Last result coming in!'
            self._data = self._tmp_data
            self._tmp_data = np.array([])

    def retrieve_result(self):
        """ Returns the record changes for the current pixel

        Result is stored as a list of dictionaries

        Note:   MATLAB indexes on 1 so y is really (y - 1) in calculations and
                x is (x - 1)

        """
        self.result = []

        # Check for existence of output
        record = self.results_pattern.replace(
            '*', str(self._py + 1)) + '.mat'

        record = os.path.join(self.location, self.results_folder, record)

        print 'Opening: {r}'.format(r=record)

        if not os.path.exists(record):
            print 'Warning: cannot find record for row {r}: {f}'.format(
                r=self._py + 1, f=record)
            return

        # Calculate MATLAB position for x, y
        pos = (self._py * self.x_size) + self._px + 1

        print '    position: {p}'.format(p=pos)

        # Read .mat file as ndarray of scipy.io.matlab.mio5_params.mat_struct
        mat = scipy.io.loadmat(record, squeeze_me=True,
                               struct_as_record=False)['rec_cg']

        # Loop through to find correct x, y
        for i in xrange(mat.shape[0]):
            if mat[i].pos == pos:
                self.result.append(mat2dict(mat[i]))

    def get_data(self, mask=True):
        """ Return time series dataset with options to mask/unmask
        """
        if mask is False:
            return np.array(self._data)
        else:
            return self._data

    def get_prediction(self, band, usermx=None):
        """ Return the time series model fit predictions for any single pixel

        Arguments:
            band            time series band to predict
            usermx          optional - can specify MATLAB datenum dates as list

        Returns:
            [(mx, my)]      list of data points for time series fit where
                                length of list is equal to number of time
                                segments

        """
        if usermx is None:
            has_mx = False
        else:
            has_mx = True
        mx = []
        my = []

        if len(self.result) > 0:
            for rec in self.result:
                if band >= rec['coefs'].shape[1]:
                    break

                ### Setup x values (dates)
                # Use user specified values, if possible
                if has_mx:
                    _mx = usermx[np.where((usermx >= rec['t_start']) &
                                          (usermx <= rec['t_end']))]
                    if len(_mx) == 0:
                        # User didn't ask for dates in this range
                        continue
                else:
                # Create sequence of MATLAB ordinal date
                    _mx = np.linspace(rec['t_start'],
                                      rec['t_end'],
                                      max(1, rec['t_end'] - rec['t_start']))
                coef = rec['coefs'][:, band]

                ### Calculate model predictions
                w = 2 * np.pi / self.days_in_year

                if coef.shape[0] == 2:
                    _my = (coef[0] +
                           coef[1] * _mx)
                elif coef.shape[0] == 4:
                    # 4 coefficient model
                    _my = (coef[0] +
                           coef[1] * _mx +
                           coef[2] * np.cos(w * _mx) +
                           coef[3] * np.sin(w * _mx))
                elif coef.shape[0] == 6:
                    # 6 coefficient model
                    _my = (coef[0] +
                           coef[1] * _mx +
                           coef[2] * np.cos(w * _mx) +
                           coef[3] * np.sin(w * _mx) +
                           coef[4] * np.cos(2 * w * _mx) +
                           coef[5] * np.sin(2 * w * _mx))
                elif coef.shape[0] == 8:
                    # 8 coefficient model
                    _my = (coef[0] +
                           coef[1] * _mx +
                           coef[2] * np.cos(w * _mx) +
                           coef[3] * np.sin(w * _mx) +
                           coef[4] * np.cos(2 * w * _mx) +
                           coef[5] * np.sin(2 * w * _mx) +
                           coef[6] * np.cos(3 * w * _mx) +
                           coef[7] * np.sin(3 * w * _mx))
                else:
                    break
                ### Transform MATLAB ordinal date into Python datetime
                _mx = [dt.datetime.fromordinal(int(m)) -
                       dt.timedelta(days=366) for m in _mx]
                ### Append
                mx.append(np.array(_mx))
                my.append(np.array(_my))

        return (mx, my)

    def get_breaks(self, band):
        """ Return an array of (x, y) data points for time series breaks """
        bx = []
        by = []
        if len(self.result) > 1:
            for rec in self.result:
                if rec['t_break'] != 0:
                    bx.append(dt.datetime.fromordinal(int(rec['t_break'])) -
                              dt.timedelta(days=366))
                    print 'Break: %s' % str(bx)
                    index = [i for i, date in
                             enumerate(self.dates) if date == bx[-1]][0]
                    print 'Index: %s' % str(index)
                    if index < self._data.shape[1]:
                        by.append(self._data[band, index])

        return (bx, by)

    def get_px(self):
        """ Returns current pixel column number """
        return self._px

    def set_px(self, x):
        """ Set current pixel column number """
        if x < 0:
            raise ValueError('x cannot be below 0')
        elif x > self.x_size:
            raise ValueError('x cannot be larger than the image')
        elif x is None:
            raise ValueError('x cannot be None')
        else:
            self._px = x

    def get_py(self):
        """ Returns current pixel row number """
        return self._py

    def set_py(self, y):
        """ Set current pixel row number """
        if y < 0:
            raise ValueError('y cannot be below 0')
        elif y > self.y_size:
            raise ValueError('y cannot be larger than the image')
        elif y is None:
            raise ValueError('y cannot be None')
        else:
            self._py = y

### OVERRIDEN "ADDITIONAL" OPTIONAL METHODS SUPPORTED BY CCDCTimeSeries
    def apply_mask(self, mask_band=None, mask_val=None):
        """ Apply mask to self._data """

        if mask_band is None:
            mask_band = self.mask_band

        if mask_val is None:
            mask_val = list(self.mask_val)

        self._data = np.array(self._data)

        # Mask band - 1  since GDAL is index on 1, but NumPy is index on 0
        mask = np.ones_like(self._data) * np.logical_or.reduce(
            [self._data[mask_band - 1, :] == mv for mv in mask_val])

        self._data = np.ma.MaskedArray(self._data, mask=mask)

    def retrieve_from_cache(self):
        """ Try retrieving a pixel timeseries from cache

        Return True, False or Exception depending on success

        """
        cache = self.cache_name_lookup(self._px, self._py)

        if self.read_cache and os.path.exists(cache):
            try:
                _read_data = np.load(cache)
            except:
                print 'Error: could not open pixel {x}/{y} from cache ' \
                    'file'.format(x=self._px, y=self._py)
                print sys.exc_info()[0]
                raise
            else:
                # Test if newly read data is same size as current
                if _read_data.shape != self._data.shape:
                    print 'Warning: cached data may be out of date'
                    return False

                self._data = _read_data

                # We've read data, apply mask and return True
                self.apply_mask()

                return True

        return False

    def write_to_cache(self):
        """ Write retrieved time series to cache

        Return True, False, or Exception depending on success

        Note:   writing of NumPy masked arrays is not implemented, so stick to
                regular ndarray

        """
        cache = self.cache_name_lookup(self._px, self._py)

        if self.write_cache and not os.path.exists(cache):
            try:
                np.save(cache, np.array(self._data))
            except:
                logger.error('Error: could not write pixel {x}/{y} to cache '
                             'file'.format(x=self._px, y=self._py))
                logger.error(sys.exc_info()[0])
                raise
            else:
                logger.info('Wrote to cache')
                return True

        return False

### INTERNAL SETUP METHODS
    def _find_stacks(self):
        """ Find and set names for Landsat image stacks """
        # Setup lists
        self.image_names = []
        self.filenames = []
        self.filepaths = []

        # Populate - only checking one directory down
        self.location = self.location.rstrip(os.path.sep)
        num_sep = self.location.count(os.path.sep)
        for root, dnames, fnames in os.walk(self.location, followlinks=True):
            if self.results_folder is not None and self.results_folder != '':
                # Remove results folder if exists
                dnames[:] = [d for d in dnames if
                             self.results_folder not in d]

            # Force only 1 level
            num_sep_this = root.count(os.path.sep)
            if num_sep + 1 <= num_sep_this:
                del dnames[:]

            # Directory names as image IDs
            for dname in fnmatch.filter(dnames, self.image_pattern):
                self.image_names.append(dname)
            # Add file name and paths
            for fname in fnmatch.filter(fnames, self.stack_pattern):
                self.filenames.append(fname)
                self.filepaths.append(os.path.join(root, fname))

        # Check for consistency
        if len(self.image_names) != len(self.filenames) != len(self.filepaths):
            raise Exception(
                'Inconsistent number of stacks and stack directories')

        self.length = len(self.image_names)
        if self.length == 0:
            raise Exception('Zero stack images found')

        # Sort by image name/ID (i.e. Landsat ID)
        self.image_names, self.filenames, self.filepaths = (
            list(t) for t in zip(*sorted(zip(self.image_names,
                                             self.filenames,
                                             self.filepaths)))
            )

    def _get_attributes(self):
        """ Fetch image stack attributes including number of rows, columns,
        bands, the geographic transform, projection, file format, data type,
        and band names

        """
        # Based on first stack image
        stack = self.filepaths[0]

        # Open with GDAL
        gdal.AllRegister()
        ds = gdal.Open(stack, gdal.GA_ReadOnly)
        if ds is None:
            raise Exception('Could not open {stack} as dataset'.format(
                stack=stack))

        # Raster size
        self.x_size = ds.RasterXSize
        self.y_size = ds.RasterYSize
        self.n_band = ds.RasterCount

        # Geographic transform & projection
        self.geo_transform = ds.GetGeoTransform()
        self.projection = ds.GetProjection()

        # File type and format
        self.fformat = ds.GetDriver().ShortName
        if self.fformat == 'ENVI':
            interleave = ds.GetMetadata('IMAGE_STRUCTURE')['INTERLEAVE']
            if interleave == 'PIXEL':
                self.fformat = 'BIP'
            elif interleave == 'BAND':
                self.fformat = 'BSQ'

        # Data type
        self.datatype = gdal.GetDataTypeName(ds.GetRasterBand(1).DataType)
        if self.datatype == 'Byte':
            self.datatype = 'uint8'
        self.datatype = np.dtype(self.datatype)

        # Band names
        self.band_names = []
        for i in range(ds.RasterCount):
            band = ds.GetRasterBand(i + 1)
            if (band.GetDescription() is not None and
                    len(band.GetDescription()) > 0):
                self.band_names.append(band.GetDescription())
            else:
                self.band_names.append('Band %s' % str(i + 1))

        ds = None

    def _get_dates(self):
        """ Get image dates as Python datetime
        """
        self.dates = []
        for image_name in self.image_names:
            self.dates.append(dt.datetime.strptime(image_name[9:16], '%Y%j'))
#            self.dates.append(dt.datetime(int(image_name[9:13]), 1, 1) +
#                              dt.timedelta(int(image_name[13:16]) - 1))
        self.dates = np.array(self.dates)

        # Sort images by date
        self.dates, self.image_names, self.filenames, self.filepaths = (
            list(t) for t in zip(*sorted(zip(
                self.dates, self.image_names, self.filenames, self.filepaths)))
        )
        self.dates = np.array(self.dates)

    def _check_results(self):
        """ Checks for results """
        results = os.path.join(self.location, self.results_folder)
        if (os.path.exists(results) and os.path.isdir(results) and
                os.access(results, os.R_OK)):
            # Check for any results
            for root, dname, fname in os.walk(results):
                for f in fnmatch.filter(fname, self.results_pattern):
                    self.has_results = True
                    self.results_folder = root
                    return

    def _open_ts(self):
        """ Open timeseries as list of ImageReaders """
        self.readers = []
        for stack in self.filepaths:
            self.readers.append(
                ImageReader(stack,
                            self.fformat,
                            self.datatype,
                            (self.y_size, self.x_size),
                            self.n_band))

    def _get_metadata(self):
        """ Parse timeseries attributes for metadata """
        # Sensor ID
        self.sensor = np.array([n[0:3] for n in self.image_names])
        # Path/Row
        self.pathrow = np.array(['p{p}r{r}'.format(p=n[3:6], r=n[6:9])
                                for n in self.image_names])

### Additional methods dealing with caching
    def cache_name_lookup(self, x, y):
        """ Return cache filename for given x/y """
        cache = 'n{n}_x{x}-y{y}_timeseries.npy'.format(
            n=self.length, x=x, y=y)
        if self.cache_folder is not None:
            return os.path.join(self.location, self.cache_folder, cache)
        else:
            return None
