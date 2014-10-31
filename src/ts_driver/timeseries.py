# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Timeseries base class
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@gmail.com
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
import abc
import datetime as dt
import os

import numpy as np
from osgeo import gdal
import scipy.io


class AbstractTimeSeries(object):
    """ Abstract base class representing a remote sensing time series.

    AbstractTimeSeries class is meant to be sub-classed and its methods
    overriden. This interface simply defines attributes and methods expected
    by "TSTools" QGIS plugin.

    Required attributes:
        image_names                 Names or IDs for each image
        filenames                   File basename for each image
        filepaths                   Full path to each image
        length                      Number of images in time series
        dates                       np.array of datetime for each image
        n_band                      number of bands per image
        x_size                      number of columns per image
        y_size                      number of rows per image
        geo_transform               geo-transform of images
        projection                  projection of images
        px                          current pixel column
        py                          current pixel row
        has_results                 boolean indicating existence of model fit

    Required methods:
        fetch_pixel                 retrieve pixel data for given x/y
        fetch_result                retrieve result for given x/y
        get_data                    return dataset
        get_prediction              return predicted dataset for x/y
        get_breaks                  return break points for time segments

    Additional attributes:
        read_cache                  boolean indicating existence of cached data
        write_cache                 boolean indicating potential to cache data
        cache_folder                location of cache, if any
        mask_band                   band (index on 0) of mask within images
        mask_val                    values to mask
        metadata                    list of attributes containing metadata
        metadata_str                list of strings describing metadata
        symbology_hint_indices      list of default indices for RGB symbology
        symbology_hint_minmax       tuple of min, max for RGB symbology

    Additional methods:
        apply_mask                  apply mask to dataset
        retrieve_from_cache         retrieve dataset from cached retrieval
        write_to_cache              write retrieved dataset to cache

    """

    __metaclass__ = abc.ABCMeta

    # Overide/set these within subclasser as needed
    read_cache = False
    write_cache = False
    cache_folder = None
    mask_band = None
    mask_val = None
    metadata = []
    metadata_str = []

    symbology_hint_indices = (4, 3, 2)
    # Specify two numbers (int or float) for one min/max for all bands
    # OR specify np.ndarray for each band in dataset for min and max
    #     e.g. symbology_hint_minmax = (np.zeros(8), np.ones(8) * 10000)
    symbology_hint_minmax = (0, 10000)

    def __init__(self, location, image_pattern, stack_pattern):
        # Basic, required information
        self.location = os.path.realpath(location)
        self.image_pattern = image_pattern
        self.stack_pattern = stack_pattern

    def __repr__(self):
        return 'A {c} time series of {n} images at {m}'.format(
            c=self.__class__.__name__, n=self.length, m=hex(id(self)))

# ADDITIONAL METHODS: override/set by subclasser as needed
    def apply_mask(self, mask_band=None, mask_val=None):
        """ Use subclasser to set if capability is available """
        pass

    def retrieve_from_cache(self, x, y):
        """ Use subclasser to set if capability is available """
        return False

    def write_to_cache(self):
        """ Use subclasser to set if capability is available """
        return False

# REQUIRED PROPERTIES
    @abc.abstractproperty
    def image_names(self):
        """ Common names or IDs for each image """
        pass

    @abc.abstractproperty
    def filenames(self):
        """ File basename for each image """
        pass

    @abc.abstractproperty
    def filepaths(self):
        """ Full path to each image """
        pass

    @abc.abstractproperty
    def length(self):
        """ Length of the time series """
        pass

    @abc.abstractproperty
    def dates(self):
        """ np.array of datetime for each image """
        pass

    @abc.abstractproperty
    def n_band(self):
        """ number of bands per image """
        pass

    @abc.abstractproperty
    def x_size(self):
        """ number of columns per image """
        pass

    @abc.abstractproperty
    def y_size(self):
        """ number of rows per image """
        pass

    @abc.abstractproperty
    def geo_transform(self):
        """ geo-transform for each image """
        pass

    @abc.abstractproperty
    def projection(self):
        """ projection for each image """
        pass

    @abc.abstractproperty
    def has_results(self):
        """ boolean indicating existence of model fit """
        pass


# HELPER METHOD
    def get_ts_pixel(self, x, y):
        """ Fetch pixel data for a given x/y and set to self.data

        Args:
            x                       column
            y                       row

        """
        for i in xrange(self.length):
            self.retrieve_pixel(x, y, i)

# REQUIRED METHODS
    @abc.abstractmethod
    def retrieve_pixel(self, x, y, index):
        """ Return pixel data for a given x/y and index in time series

        Args:
            x                       column
            y                       row
            index                   index of image in time series

        Returns:
            data                    n_band x 1 np.array

        """
        pass

    @abc.abstractmethod
    def retrieve_result(self, x, y):
        """ Retrieve algorithm result for a given x/y

        Args:
            x                       column
            y                       row

        """
        pass

    @abc.abstractmethod
    def get_data(self, mask=True):
        """
        """
        pass

    @abc.abstractmethod
    def get_prediction(self, band):
        """
        """
        pass

    @abc.abstractmethod
    def get_breaks(self, x, y):
        """
        """
        pass

    @abc.abstractmethod
    def get_px(self):
        """ current pixel column number """
        pass

    @abc.abstractmethod
    def set_px(self, value):
        """ set current pixel column number """
        pass

    @abc.abstractmethod
    def get_py(self):
        """ current pixel row number """
        pass

    @abc.abstractmethod
    def set_py(self, value):
        """ set current pixel row number """
        pass

    _px = abc.abstractproperty(get_px, set_px)
    _py = abc.abstractproperty(get_py, set_py)


# Utility reader class
class ImageReader(object):
    """
    This class defines the methods for reading pixel values from a raster
    dataset. I've coded this up because certain file formats are more
    efficiently accessed via fopen than via GDAL (i.e. BIP).

    http://osdir.com/ml/gdal-development-gis-osgeo/2007-04/msg00345.html

    If the fformat isn't a BIP, then we just use GDAL. In the future we can
    probably code it better for BIL and maybe BSQ.

    Args:
    filename                    filename of the raster to read from
    fformat                     file format of the raster
    dt                          numpy datatype
    size                        list of [nrow, ncol]
    n_band                      number of bands in image
    """
    def __init__(self, filename, fformat, dt, size, n_band):
        self.filename = filename
        self.fformat = fformat
        self.dt = dt
        self.size = size
        self.n_band = n_band

        # Switch the actual definition of get_pixel by fformat
        # TODO: reimplement this using class inheritance
        # https://www.youtube.com/watch?v=miGolgp9xq8
        if fformat == 'BIP':
            self.get_pixel = self.__BIP_get_pixel
        else:
            self.get_pixel = self.__band_get_pixel

    def __BIP_get_pixel(self, row, col):
        if row < 0 or row >= self.size[0] or col < 0 or col >= self.size[1]:
            raise ValueError('Cannot select row,col %s,%s' % (row, col))

        with open(self.filename, 'rb') as f:
            # Skip to location of data in file
            f.seek(self.dt.itemsize * (row * self.size[1] + col) *
                   self.n_band)
            # Read in
            dat = np.fromfile(f, dtype=self.dt, count=self.n_band)
        return dat

    def __band_get_pixel(self, row, col):
        if row < 0 or row >= self.size[0] or col < 0 or col >= self.size[1]:
            raise ValueError('Cannot select row,col %s,%s' % (row, col))

        ds = gdal.Open(self.filename, gdal.GA_ReadOnly)

        pixels = np.zeros(self.n_band)

        for i in range(ds.RasterCount):
            b = ds.GetRasterBand(i + 1)
            pixels[i] = b.ReadAsArray(col, row, 1, 1)

        ds = None

        return pixels

# Utility functions
def mat2dict(matlabobj):
    """
    Utility function:
    Converts a scipy.io.matlab.mio5_params.mat_struct to a dictionary
    """
    d = {}
    for field in matlabobj._fieldnames:
        value = matlabobj.__dict__[field]
        if isinstance(value, scipy.io.matlab.mio5_params.mat_struct):
            d[field] = mat2dict(value)
        else:
            d[field] = value
    return d

def ml2pydate(ml_date):
    """
    Utility function:
    Returns Python datetime for MATLAB date
    """
    return dt.datetime.fromordinal(int(ml_date)) - dt.timedelta(days = 366)

def py2mldate(py_date):
    """
    Utility function:
    Returns MATLAB datenum for Python datetime
    """
    return (py_date + dt.timedelta(days = 366)).toordinal()
