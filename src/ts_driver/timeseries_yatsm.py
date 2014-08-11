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
from datetime import datetime as dt
import logging

import numpy as np
try:
    from osgeo import gdal
except:
    import gdal

import timeseries_ccdc


class YATSM_LIVE(timeseries_ccdc.CCDCTimeSeries):
    """Class holding data and methods for time series used by CCDC
    (Change Detection and Classification). Useful for QGIS plugin 'TSTools'.

    More doc TODO
    """

    # __str__ name for TSTools data model plugin loader
    __str__ = 'YATSM Live Plotter'

    __configurable__ = ['image_pattern', 'stack_pattern',
                        'cache_folder', 'mask_band']
    __configurable__str__ = ['Image folder pattern',
                             'Stack pattern',
                             'Cache folder',
                             'Mask band']

    crossvalidate_lambda = False
    consecutive = 5
    min_obs = 12
    threshold = 2.57
    enable_min_rmse = False
    min_rmse = 0.0
    freq = np.array([1, 2, 3])
    reverse = False
    test_indices = np.array([3, 4, 5, 6])
    robust_results = False
    debug = False

    __custom_controls_title__ = 'YATSM Options'
    __custom_controls__ = ['crossvalidate_lambda',
                           'consecutive', 'min_obs', 'threshold',
                           'enable_min_rmse', 'min_rmse',
                           'freq', 'reverse',
                           'test_indices', 'robust_results',
                            'debug']

    def __init__(self, location, config=None):

        super(YATSM_LIVE, self).__init__(location, config)

        self.ord_dates = np.array(map(dt.toordinal, self.dates))
        self.X = None
        self.Y = None
        self._check_yatsm()

    def set_custom_controls(self, values):
        """ Set custom control options

        Arguments:
            values          list of values to be inserted into OrderedDict

        """
        for v, k in zip(values, self.__custom_controls__):
            current_value = getattr(self, k)
            if isinstance(v, type(current_value)):
                # Check if we need to update the frequency of X
                if k == 'freq':
                    if any([_v not in self.freq for _v in v]) or \
                            any([_f not in v for _f in self.freq]):
                        self.X = make_X(self.ord_dates, v).T
                setattr(self, k, v)
            else:
                # Make an exception for minimum RMSE since we can pass None
                if k == 'min_rmse' and isinstance(v, float):
                    setattr(self, k, v)
                else:
                    print 'Error setting value for {o}'.format(o=k)
                    print current_value, v

    def retrieve_result(self):
        """ Returns the record changes for the current pixel
        """
        # Note: X recalculated during variable setting, if needed, unless None
        if self.X is None:
            self.X = make_X(self.ord_dates, self.freq).T
        # Get Y
        self.Y = self.get_data(mask=False)
        clear = self.Y[self.mask_band - 1, :] <= 1

        # Turn on/off minimum RMSE
        if not self.enable_min_rmse:
            self.min_rmse = None

        if self.debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        if self.reverse:
            self.yatsm_model = YATSM(np.flipud(self.X[clear, :]),
                                     np.fliplr(self.Y[:-1, clear]),
                                     consecutive=self.consecutive,
                                     threshold=self.threshold,
                                     min_obs=self.min_obs,
                                     min_rmse=self.min_rmse,
                                     lassocv=self.crossvalidate_lambda,
                                     loglevel=loglevel)
        else:
            self.yatsm_model = YATSM(self.X[clear, :],
                                     self.Y[:-1, clear],
                                     consecutive=self.consecutive,
                                     threshold=self.threshold,
                                     min_obs=self.min_obs,
                                     min_rmse=self.min_rmse,
                                     lassocv=self.crossvalidate_lambda,
                                     loglevel=loglevel)

        # Run
        self.yatsm_model.run()

        # List to store results
        if self.robust_results:
            self.result = self.yatsm_model.robust_record
        else:
            self.result = self.yatsm_model.record

    def get_prediction(self, band, usermx=None):
        """ Return the time series model fit predictions for any single pixel

        Arguments:
            band            time series band to predict
            usermx          optional - can specify ordinal dates as list

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
                if band >= rec['coef'].shape[1]:
                    break

                ### Setup x values (dates)
                # Use user specified values, if possible
                if has_mx:
                    _mx = usermx[np.where((usermx >= rec['start']) &
                                 (usermx <= rec['end']))]
                    if len(_mx) == 0:
                        # User didn't ask for dates in this range
                        continue
                else:
                    # Check for reverse
                    if rec['end'] < rec['start']:
                        i_step = -1
                    else:
                        i_step = 1
                    _mx = np.arange(rec['start'],
                                    rec['end'],
                                    i_step)
                coef = rec['coef'][:, band]

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
                _mx = [dt.fromordinal(int(m)) for m in _mx]
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
                if rec['break'] != 0:
                    bx.append(dt.fromordinal(int(rec['break'])))
                    index = [i for i, date in
                             enumerate(self.dates) if date == bx[-1]][0]
                    if index < self._data.shape[1]:
                        by.append(self._data[band, index])

        return (bx, by)

### OVERRIDEN "ADDITIONAL" OPTIONAL METHODS SUPPORTED BY CCDCTimeSeries
### INTERNAL SETUP METHODS
    def _check_yatsm(self):
        """ Check if YATSM is available """
        try:
            global YATSM
            global make_X
            from ..yatsm.yatsm import YATSM, make_X
        except:
            raise Exception('Could not import YATSM')
        else:
            self.has_results = True
