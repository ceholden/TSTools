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
from collections import OrderedDict
import csv
import datetime as dt
import fnmatch
import os
import re
import sys

import numpy as np
import scipy.io
try:
    from osgeo import gdal
except:
    import gdal

import timeseries_ccdc
from timeseries import mat2dict, ml2pydate, py2mldate

# FROM: http://code.google.com/p/scidb/source/browse/trunk/mlabwrap_util.py
def is_cell_proxy(obj):
    return "<MlabObjectProxy of matlab-class: 'cell'" in str(obj)

def is_struct_proxy(obj):
    return "<MlabObjectProxy of matlab-class: 'struct'" in str(obj)

def convert(obj, mlab):
    if isinstance(obj, basestring):
        return obj
    elif isinstance(obj, np.ndarray):
        if np.shape(obj) == (1,1):
            return obj[0,0]
        else:
            return obj
    elif is_cell_proxy( obj ):
        m = re.match(".*?internal name: '(.*?)';.*?", str(obj))
        varname = m.group(1)
        arr_len = int( mlab.eval('length(%s)' % varname)[0,0] )

        cell_list = []
        for k in range(arr_len):
            matlab_idx = k+1
            cell_list.append(
                convert( mlab.eval('%s{%d}' % (varname, matlab_idx)), mlab))
        return cell_list

    elif is_struct_proxy(obj):
        m = re.match(".*?internal name: '(.*?)';.*?", str(obj))
        varname = m.group(1)
        fieldnames = convert(mlab.fieldnames(obj), mlab)
        dict = {}
        for key in fieldnames:
            dict[key] = convert(mlab.eval('%s.(\'%s\')' % (varname, key) ),
                                mlab)

        return dict


class CCDCTimeSeries_v9LIVE(timeseries_ccdc.CCDCTimeSeries):
    """Class holding data and methods for time series used by CCDC
    (Change Detection and Classification). Useful for QGIS plugin 'TSTools'.

    More doc TODO
    """

    # __str__ name for TSTools data model plugin loader
    __str__ = 'CCDC v9 Time Series - LIVE'

    __configurable__ = ['image_pattern', 'stack_pattern',
        'cache_folder', 'mask_band']
    __configurable__str__ = ['Image folder pattern',
        'Stack pattern',
        'Cache folder',
        'Mask band']

    CCDC_function = 'TrendSeasonalFit_v9_QGIS_max'
    n_times = 3
    conse = 5
    T_cg = 2.57
    num_c = 8
    B_detect = np.array([[3, 4, 5, 6]])

    __custom_controls_title__ = 'CCDC v9 Options'
    __custom_controls__ = ['CCDC_function', 'n_times', 'conse',
        'T_cg', 'num_c', 'B_detect']

    def __init__(self, location, config=None):

        super(CCDCTimeSeries_v9LIVE, self).__init__(location, config)

        self.ml_dates = [py2mldate(_d) for _d in self.dates]

        self._check_matlab()

    def set_custom_controls(self, values):
        """ Set custom control options

        Arguments:
            values          list of values to be inserted into OrderedDict

        """
        for v, k in zip(values, __custom_controls__):
            current_value = getattr(self, k)
            if isinstance(v, type(current_Value)):
                if k == 'CCDC_function':
                    try:
                        self._check_matlab(function=v, load_ml=False)
                    except:
                        raise
                setattr(self, k, v)
            else:
                print 'Error setting value for {o}'.format(
                    o=k)

    def retrieve_result(self):
        """ Returns the record changes for the current pixel

        Result is stored as a list of dictionaries

        Note:   MATLAB indexes on 1 so y is really (y - 1) in calculations and
                x is (x - 1)

        CCDC Usage:cd
            rec_cg=TrendSeasonalFit_v10_QGIS(
                N_row,N_col, mini, T_cg, n_times, conse, B_detect)

        """
        # Check that MATLAB is still active
        try:
            self.mlab.eval('1 + 1')
        except:
            try:
                # Re-open MATLAB
                mlabwrap.mlab = mlabwrap.MlabWrap()
                from mlabwrap import mlab
                self.mlab = mlabwrap.mlab
            except:
                print 'Cannot open MATLAB - is it still running?'
                raise

        if self.CCDC_folder not in self.mlab.path():
            for d in [_d[0] for _d in os.walk(self.CCDC_folder)]:
                self.mlab.path(self.mlab.path(), d)

        # List to store results
        self.result = []

        ### Set data in MATLAB
        self.mlab._set('sdate', self.ml_dates)
        self.mlab._set('line_t', self.get_data(mask = False).T)

        for k in self.__custom_controls__:
            v = getattr(self, k)
            self.mlab._set(k, v)
 #       for k, v in self.param.iteritems():
 #           self.mlab._set(str(k), v)

        ### Run CCDC in MATLAB and save MATLAB proxy class from mlabwrap
        rec_cg = self.mlab.eval(self.CCDC_function +
            '(sdate, line_t, n_times, conse, T_cg, num_c, B_detect);')

        # Find how many records using MATLAB commands
        n_records = int(self.mlab.size(rec_cg)[0][1])

        for i in range(n_records):
            # Convert references to MATLAB structs to dictionaries and append
            self.result.append(convert(rec_cg[i], self.mlab))

        print self.result


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
                                      rec['t_end'] - rec['t_start'])
                coef = rec['coefs'][:, band]

                ### Calculate model predictions
                w = 2 * np.pi / 365.25

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
                                dt.timedelta(days = 366)
                                for m in _mx]
                ### Append
                mx.append(np.array(_mx))
                my.append(np.array(_my))

        return (mx, my)


### OVERRIDEN "ADDITIONAL" OPTIONAL METHODS SUPPORTED BY CCDCTimeSeries


### INTERNAL SETUP METHODS
    def _check_matlab(self, folder='CCDC',
                      function='TrendSeasonalFit_v9_QGIS_max',
                      load_ml=True):
        """ Check to see if MATLAB files are available and can be loaded
        """

        if load_ml is True:
            # Try to load MATLAB
            try:
                import mlabwrap
                from mlabwrap import mlab
                self.mlab = mlabwrap.mlab
            except:
                print 'Error: cannot import MATLAB'
                raise

        # Check for source code detailed in method arguments
        import inspect
        here = os.path.abspath(
            os.path.dirname(inspect.getfile(self.__class__)))

        folder = os.path.join(here, folder)
        if not os.path.isdir(folder):
            print folder
            raise ImportError, 'cannot find CCDC source code folder'
        else:
            folder = os.path.abspath(folder)

        fn = []
        for root, directory, f in os.walk(here):
            for result in fnmatch.filter(f, function + '.m'):
                fn.append(os.path.join(root, result))

        if len(fn) > 1:
            raise ImportError, 'found more than one function matching description'
        else:
            f = fn[0]

        if not os.path.isfile(f):
            raise ImportError, 'cannot find CCDC source code flie'

        self.CCDC_function = function
        self.CCDC_folder = folder
        self.has_results = True
