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

class CCDCTimeSeries:

    def __init__(self, location, image_pattern='LND*', 
                 stack_pattern='*stack'):
        # Keep location of stacks   
        self.location = location
        
        ### Try to find stacks
        # image_ids -> Landsat IDs i.e. directory names
        self.image_ids = []
        # files - basenames of stacks
        self.files = []
        # stacks - full filenames
        self.stacks = []
        # length - number of images
        self.length = 0
        # Find stack ids, files, stack names and length
        self._find_stacks(image_pattern, stack_pattern)

        # Gather geo-attributes
        self._get_attributes()
        # Get stack dates
        self.dates = []
        self._get_stack_dates()
        # Get stack time series information
        self.has_reccg = True
        self.reccgmat = {}
        self.has_reccgmat = self._get_record_changes()

        # Initialize data
        self.x = 0
        self.y = 0
        self.data = np.zeros([self.n_band, self.length])
        self.reccg = []
        
        # Open the files
        self.open_ts()

        # TODO: store some number of last fetches... don't re-retrieve if x-y
        # in this list for tradeoff of more memory but better performance?
    
    def __repr__(self):
        return 'A CCDCTimeSeries of %s images at %s' % (
            str(self.length), str(hex(id(self))))

    def _find_stacks(self, image_pattern, stack_pattern):
        """ 
        Finds & sets names for Landsat image directories & stacks
        """
        for root, dnames, fnames in os.walk(self.location, followlinks=True):
            for dname in fnmatch.filter(dnames, image_pattern):
                self.image_ids.append(dname)
            for fname in fnmatch.filter(fnames, stack_pattern):
                self.files.append(fname)
                self.stacks.append(os.path.join(root, fname))

        # TODO: handle this error more intelligently
        if len(self.image_ids) > len(self.stacks):
            print 'Error: one or more stacks missing/not found'
            return
        elif len(self.image_ids) < len(self.stacks):
            print 'Error: more than one stack found for a directory'
            return
        self.length = len(self.stacks)
        if self.length == 0:
            raise CCDCLengthError(self.length)
        # Sort both by image name (i.e. Landsat ID)
        self.image_ids, self.files, self.stacks = (list(t) for t in 
            zip(*sorted(zip(self.image_ids, self.files, self.stacks))))

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
                self.band_names.append('Band %s' % str(iBand + 1))
        
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
        for image_id in self.image_ids:
            self.dates.append(dt.datetime(int(image_id[9:13]), 1, 1) + 
                dt.timedelta(int(image_id[13:16]) - 1))

    def _get_record_changes(self, basename='record_change'):
        """
        Opens the output from MATLAB "record_changeXXXX.mat" files to retrieve
        the output of CCDC. Stores names in self.reccgmat dictionary as 
        {row: filename}

        Args:
            basename:   basename for record changes (currently record_change)
        """
        # Check for TSFitMap
        if os.path.islink(self.location + '/TSFitMap'):
            loc = os.path.realpath(self.location + '/TSFitMap')
            if not loc.endswith('/'):
                loc = loc + '/'
        elif os.path.isdir(self.location + '/TSFitMap'):
            loc = self.location + '/TSFitMap/'
        else:
            return False

        files = os.listdir(loc)
        for filename in fnmatch.filter(files, basename + '*'):
            # Row = filename row - 1 since we start on 0
            row = int(filename.replace(basename, '').replace('.mat', '')) - 1
            self.reccgmat[row] = loc + filename
        
        if len(self.reccgmat) == 0:
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
                self.datatype, [self.y_size, self.x_size], self.n_band)) 

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
        self.x = x
        self.y = y
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

        Note:   MATLAB indexes on 1 so y is really (y - 1) in calculations 
                and x is (x - 1)                
        """
        if x > self.x_size or x < 0 or y > self.y_size or y < 0:
            return
        if not y in self.reccgmat.keys():
            print 'Could not find row %i in keys...' % (y + 1)
            return
        # Fetch the position value for given x, y
        pos = (y * self.x_size) + x + 1
        # Read mat file as ndarray of scipy.io.matlab.mio5_params.mat_struct
        print 'Opening %s' % self.reccgmat[y]
        mat = scipy.io.loadmat(self.reccgmat[y], squeeze_me=True,
            struct_as_record=False)['rec_cg']
        # Store the time series fits as dictionary
        self.reccg = []
        # Loop through (ugh) to find correct x,y
        for i in xrange(mat.shape[0]):
            if mat[i].pos == pos:
                self.reccg.append(mat2dict(mat[i]))

    def get_prediction(self, band, usermx=None):
        """
        Return the time series model fit predictions for any single pixel.

        Arguments:
            band            Band to predict in the layer stack
            mx              Optional; can specify MATLAB datenum dates as list
        """
        if usermx is None:
            has_mx = False
        else:
            has_mx = True
        mx = []
        my = []

        if len(self.reccg) > 0:
            for rec in self.reccg:
                if band >= rec['coefs'].shape[1]:
                    break
                
                ### Setup x values (dates)
                # Use user specified values, if possible
                if has_mx:
                    _mx = usermx[np.where((usermx >= rec['t_start']) & 
                                      (usermx <= rec['t_end']))]
                    if len(_mx) == 0: # User didn't ask for dates in this range
                        continue
                else:
                 # Create sequence of MATLAB ordinal date
                    _mx = np.linspace(rec['t_start'],
                                      rec['t_end'],
                                      rec['t_end'] - rec['t_start'])
                coef = rec['coefs'][:, band]
                
                ### Calculate model predictions
                w = 2 * np.pi / 365
                if coef.shape[0] == 4:
                    # 4 coefficient model
                    _my = (coef[0] +
                            coef[1] * _mx +
                            coef[2] * np.cos(w * _mx) +
                            coef[3] * np.sin(w * _mx))
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
                                dt.timedelta(days = 366)
                                for m in _mx]
                ### Append
                mx.append(_mx)
                my.append(_my)

        return (mx, my)

    def get_breaks(self, band):
        """
        Return an array of x,y points for time series breaks
        """
        bx = []
        by = []
        if len(self.reccg) > 1:
            for rec in self.reccg[0:-1]:
                bx.append(dt.datetime.fromordinal(int(rec['t_break'])) -
                      dt.timedelta(days = 366))
                print 'Break: %s' % str(bx)
                index = [i for i, date in 
                        enumerate(self.dates) if date == bx[-1]][0]
                print 'Index: %s' % str(index)
                if index < self.data.shape[1]:
                    by.append(self.data[band, index])
        return (bx, by)
                    


# TODO: delete this... it is stupid and should be replaced with length error
# or something
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
