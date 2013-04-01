# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCTimeSeries
                                 A QGIS plugin
 Plotting & visualization tools for CCDC Landsat time series analysis
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
import os

import numpy as np
import numpy.ma as ma
import scipy.io

from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly

from ccdc_binary_reader import CCDCBinaryReader


class CCDCTimeSeries:
    def __init__(self, location, image_pattern, stack_pattern):
        # Keep location of stacks   
        self.location = location
        
        # Try to find stacks
        self.images = []
        self.stacks = []
        self._find_stacks(image_pattern, stack_pattern)

        # Gather geo-attributes
        self._get_attributes()
        # Get stack dates
        self.dates = []
        self._get_stack_dates()
        # Get stack time series information
        self.has_reccg = True
        self.reccg = {}
        self.has_reccg = self._get_record_changes()

        # Initialize data
        self.data = np.zeros([self.n_band, self.length])
        
        # Open the files
        self.open_ts()

        # TODO: store some number of last fetches... don't re-retrieve if x-y
        # in this list for tradeoff of more memory but better performance?
    
    def _find_stacks(self, image_pattern, stack_pattern):
        """ 
        Finds & sets names for Landsat image directories & stacks
        """
        for root, dnames, fnames in os.walk(self.location):
            for dname in fnmatch.filter(dnames, image_pattern):
                self.images.append(dname)
            for fname in fnmatch.filter(fnames, stack_pattern):
                self.stacks.append(os.path.join(root, fname))
        # TODO: handle this error more intelligently
        if len(self.images) > len(self.stacks):
            print 'Error: one or more stacks missing/not found'
            return
        elif len(self.images) < len(self.stacks):
            print 'Error: more than one stack found for a directory'
            return
        self.length = len(self.stacks)
        if self.length == 0:
            raise CCDCLengthError(self.length)
        # Sort both by image name (i.e. Landsat ID)
        self.images, self.stacks = (list(t) for t in 
            zip(*sorted(zip(self.images, self.stacks))))

    def _get_attributes(self):
		"""
		Fetches image stack attributes including rows, columns, bands,
		geographic transform, projection, file format, data type, band names
		"""
        # Check out the first stack in series
        stack = self.stacks[0]
        # Open and gather info from GDAL
        gdal.AllRegister()
        ds = gdal.Open(stack, GA_ReadOnly)
        if ds is None:
            print 'Could not open %s dataset' % stack
        
        # Raster size
        self.x_size = ds.RasterXSize
        self.y_size = ds.RasterYSize
        self.n_band = ds.RasterCount
        
        # Geographic transform & info
        self.geo_transform = ds.GetGeoTransform()
        self.projection = ds.GetProjection()
       
         # File type & format
        self.fformat = ds.GetDriver().ShortName
        if self.fformat == 'ENVI':
            interleave = ds.GetMetadata('IMAGE_STRUCTURE')['INTERLEAVE']
            if interleave == 'PIXEL':
                self.fformat = 'BIP'
            elif interleave == 'BAND':
                self.fformat = 'BSQ'
        
        # Data type
        band = ds.GetRasterBand(1)
        self.datatype = gdal.GetDataTypeName(band.DataType)
        if self.datatype == 'Byte':
            self.datatype = 'uint8'
        self.datatype = np.dtype(self.datatype)
        
        # Band names
        self.band_names = []
        for iBand in range(ds.RasterCount):
            band = ds.GetRasterBand(iBand + 1)
            if (band.GetDescription() is not None and
                len(band.GetDescription()) > 0):
                self.band_names.append(band.GetDescription())
            else:
                self.band_names.append('Band %s' + str(iBand + 1))
        
        # Close band & dataset
        band = None
        ds = None

    def _get_stack_dates(self):
        """
        Use the image IDs to retrieve the date as Python datetime

        Note:   Because we're trying to use YEARDOY, we have to first get the
                year and DOY seperately to create the date using:
                datetime(year, 1, 1) and then timedelta(doy - 1)
        """
        for image in self.images:
            self.dates.append(dt.datetime(int(image[9:13]), 1, 1) + 
                dt.timedelta(int(image[13:16]) - 1))

    def _get_record_changes(self, basename='record_change'):
        """
        Opens the output from MATLAB "record_changeXXXX.mat" files to retrieve
        the output of CCDC. Stores names in self.reccg dictionary as 
        {row: filename}

        Args:
            basename:   basename for record changes (currently record_change)
        """
        # Check for TSFitMap
        if not os.path.isdir(self.location + '/TSFitMap'):
            return False

        files = os.listdir(self.location + '/TSFitMap')
        for filename in fnmatch.filter(files, basename + '*'):
            # Row = filename row - 1 since we start on 0
            row = int(filename.replace(basename, '').replace('.mat', '')) - 1
            self.reccg[row] = self.location + '/TSFitMap/' + filename
        
        if len(self.reccg) == 0:
            print 'Could not find recorded changes...'
            return False
        return True

    def open_ts(self):
        """ 
        Opens the time series readers as a list of CCDCBinaryReaders
        """
        self.readers = []
        for stack in self.stacks:
            self.readers.append(
                CCDCBinaryReader(stack, self.fformat,
                self.datatype, [self.y_size, self.x_size])) 

    def get_ts_pixel(self, x, y, mask=True):
        """
        Uses the CCDCBinaryReaders in self.readers to return a NumPy
        matrix containing all bands for every date in the time series.
        
        Args:
            x:      column number (from longitude, etc.)
            y:      row number (from latitude, etc)
            mask:   use NumPy's masked array for Fmask > 1 
                        (cloud, shadow, snow)

        Returns:
            data:   NumPy matrix or masked matrix containing all bands for all
                        dates of imagery
        """
        # TODO: store x & y for quick access if already obtained (@cache)
        if x > self.x_size or x < 0 or y > self.y_size or y < 0:
            return
        for i in xrange(self.length):
            self.data[:, i] = self.readers[i].get_pixel(y, x)
        if mask:
            self.data = ma.MaskedArray(self.data, mask=(
                np.ones_like(self.data) *
                self.data[7, :] > 1))
        return self.data

    def get_reccg_pixel(self, x, y):
        """
        Returns the record changes for a given pixel
        """
        if x > self.x_size or x < 0 or y > self.y_size or y < 0:
            return
        if not y in self.reccg.keys():
            print 'Could not find row %i in keys...' % y
            return
        # Fetch the position value for given x, y (+1 for offset)
        pos = (y * self.x_size) + x + 1
        # Read mat file as ndarray of scipy.io.matlab.mio5_params.mat_struct
        mat = scipy.io.loadmat(self.reccg[y], squeeze_me=True,
            struct_as_record=False)['rec_cg']
        # Store the time series fits as dictionary
        data = []
        # Loop through (ugh) to find correct x,y
        for i in xrange(mat.shape[0]):
            if mat[i].pos == pos:
                data.append(self._todict(mat[i]))

        return data

    def _todict(self, matlabobj):
        """
        Utility function:
        Converts a scipy.io.matlab.mio5_params.mat_struct to a dictionary
        """
        d = {}
        for field in matlabobj._fieldnames:
            value = matlabobj.__dict__[field]
            if isinstance(value, scipy.io.matlab.mio5_params.mat_struct):
                d[field] = _todict(value)
            else:
                d[field] = value
        return d


class CCDCLengthError(Exception):
    """
    Raised when a time series is initialized with not enough data.

    Attributes:
        length -- number of stacks in time series
    """
    def __init__(self, length):
        self.length = length

    def __str__(self):
        return 'Stacks cannot contain %s stacks' % repr(self.length)
