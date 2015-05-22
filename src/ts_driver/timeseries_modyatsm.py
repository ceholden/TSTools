# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Yet Another TimeSeries Model for MODIS
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
from datetime import datetime as dt
import fnmatch
import logging
import os

import numpy as np
import patsy

import timeseries_yatsm

logger = logging.getLogger()


class MODYATSM_LIVE(timeseries_yatsm.YATSM_LIVE):
    """Timeseries "driver" for QGIS plugin that connects requests with model

    This is a special version which handles daily MODIS observations
    (MOD09GA/GQ) by masking according to view zenith angle.
    """

    description = 'MODYATSM Live Plotter'

    stack_pattern = 'M*D*stack.gtif'
    date_index = [5, 12]
    mask_band = 7
    vza_band = 8
    green_band = 1
    swir1_band = 4

    mask_val = [0]

    configurable = ['stack_pattern',
                    'date_index',
                    'cache_folder',
                    'mask_band',
                    'vza_band',
                    'green_band',
                    'swir1_band']
    configurable_str = ['Stack pattern',
                        'Index of date in name',
                        'Cache folder',
                        'Mask band',
                        'View Zenith Angle band',
                        'Green band',
                        'SWIR1 band']

    max_VZA = 25.0
    crossvalidate_lambda = False
    consecutive = 5
    min_obs = 16
    threshold = 3.0
    enable_min_rmse = True
    min_rmse = 100.0
    design = '1 + x + harm(x, 1)'
    reverse = False
    screen_lowess = False
    test_indices = np.array([0, 1])
    robust_results = False
    commit_test = False
    commit_alpha = 0.01
    debug = False

    custom_controls_title = 'YATSM Options'
    custom_controls = ['max_VZA',
                       'crossvalidate_lambda',
                       'consecutive', 'min_obs', 'threshold',
                       'enable_min_rmse', 'min_rmse',
                       'design', 'reverse',
                       'screen_lowess',
                       'test_indices', 'robust_results',
                       'commit_test', 'commit_alpha',
                       'debug']

    sensor = np.empty(0)
    multitemp_screened = np.empty(0)
    vza_mask = np.empty(0)

    metadata = ['sensor', 'multitemp_screened', 'vza_mask']
    metadata_str = ['Sensor', 'Multitemporal Screen', 'View Zenith Angle Mask']

    def __init__(self, location, config=None):

        super(MODYATSM_LIVE, self).__init__(location, config)

        self.ord_dates = np.array(map(dt.toordinal, self.dates))
        self.X = None
        self.Y = None
        self._check_yatsm()

    def apply_mask(self, mask_band=None, mask_val=None):
        """ Apply mask to self._data """
        logger.info('Apply mask to data')
        if mask_band is None:
            mask_band = self.mask_band

        if mask_val is None:
            mask_val = list(self.mask_val)

        self._data = np.array(self._data)

        # Mask band - 1  since GDAL is index on 1, but NumPy is index on 0
        mask = np.logical_or.reduce([self._data[mask_band - 1, :] == mv
                                    for mv in mask_val])
        valid = np.logical_and.reduce([
            (self._data[test, :] > 10000) | (self._data[test, :] < 0) for
            test in self.test_indices])
        self.vza_mask = self._data[self.vza_band - 1, :] > self.max_VZA * 100

        mask = mask | valid | self.vza_mask

        self._data = np.ma.MaskedArray(self._data,
                                       mask=mask * np.ones_like(self._data))

    def retrieve_result(self):
        """ Returns the record changes for the current pixel
        """
        self.X = patsy.dmatrix(self.design,
                               {'x': self.ord_dates,
                                'sensor': self.sensor,
                                'pr': self.pathrow})
        self.design_info = self.X.design_info

        # Get Y
        self.Y = self._data
        clear = ~self.Y.mask[0, :]

        # Turn on/off minimum RMSE
        if not self.enable_min_rmse:
            self.min_rmse = None

        # Set logger level for verbose if wanted
        level = logger.level
        if self.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        # LOWESS screening, or RLM?
        screen = 'LOWESS' if self.screen_lowess else 'RLM'

        kwargs = dict(
            consecutive=self.consecutive,
            threshold=self.threshold,
            min_obs=self.min_obs,
            min_rmse=self.min_rmse,
            test_indices=self.test_indices,
            screening=screen,
            screening_crit=self.screen_crit,
            remove_noise=self.remove_noise,
            dynamic_rmse=self.dynamic_rmse,
            design_info=self.X.design_info,
            logger=logger
        )

        if self.reverse:
            self.yatsm_model = YATSM(np.flipud(self.X[clear, :]),
                                     np.fliplr(self.Y[:-1, clear]),
                                     **kwargs)
        else:
            self.yatsm_model = YATSM(self.X[clear, :],
                                     self.Y[:-1, clear],
                                     **kwargs)

        if self.commit_test:
            self.yatsm_model.record = self.yatsm_model.commission_test(
                self.commit_alpha)

        # List to store results
        if self.robust_results:
            self.result = self.yatsm_model.robust_record
        else:
            self.result = self.yatsm_model.record

        # Reset logger level
        logger.setLevel(level)

        # Update multitemporal screening metadata
        if self.yatsm_model:
            self.multitemp_screened = np.in1d(self.X[:, 1],
                                              self.yatsm_model.X[:, 1],
                                              invert=True).astype(np.uint8)

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

                _mX = make_X(_mx, self.freq)

                ### Calculate model predictions
                _my = np.dot(coef, _mX)

                ### Transform ordinal back into Python datetime
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

    def _get_metadata(self):
        """ Parse timeseries attributes for metadata """
        # Sensor ID
        self.sensor = np.array([n[0:3] for n in self.image_names])
        # Multitemporal noise screening - init to 0 (not screened)
        #   Will update this during model fitting
        self.multitemp_screened = np.ones(self.length)
        # Make an entry 0 so we get this in the unique values
        self.multitemp_screened[0] = 0

        self.vza_mask = np.ones(self.length)
        self.vza_mask[0] = 0

### OVERRIDEN "ADDITIONAL" OPTIONAL METHODS SUPPORTED BY CCDCTimeSeries
    def _find_stacks(self):
        """ Find and set names for MODIS image stacks

        MODIS will just use the stack basename for the image ID
        """
        # Setup lists
        self.image_names = []
        self.filenames = []
        self.filepaths = []

        # Populate - only checking one directory down
        self.location = self.location.rstrip(os.path.sep)
        num_sep = self.location.count(os.path.sep)
        for root, dnames, fnames in os.walk(self.location, followlinks=True):
            if self.results_folder is not None:
                # Remove results folder if exists
                dnames[:] = [d for d in dnames if
                             self.results_folder not in d]

            # Image IDs are just basenames of files
            # Add file name and paths
            for fname in fnmatch.filter(fnames, self.stack_pattern):
                self.image_names.append(fname)
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

    def _get_dates(self):
        """ Get image dates as Python datetime
        """
        self.dates = []
        for image_name in self.image_names:
            self.dates.append(dt.strptime(
                    image_name[self.date_index[0]:self.date_index[1]],
                    '%Y%j'))

        self.dates = np.array(self.dates)

        # Sort images by date
        self.dates, self.image_names, self.filenames, self.filepaths = (
            list(t) for t in zip(*sorted(zip(
                self.dates, self.image_names, self.filenames, self.filepaths)))
        )
        self.dates = np.array(self.dates)

### INTERNAL SETUP METHODS
    def _check_yatsm(self):
        """ Check if YATSM is available """
        try:
            global YATSM
            global make_X
            from ..yatsm.yatsm import YATSM
            from ..yatsm.utils import make_X
        except:
            raise Exception('Could not import YATSM')
        else:
            self.has_results = True
