""" A driver for running YATSM on stacked Landsat/PALSAR timeseries
"""
from datetime import datetime as dt
import logging
import os

import numpy as np
import patsy

from .timeseries_yatsm import YATSMTimeSeries
from ..series import Series
from ..ts_utils import ConfigItem, find_files

logger = logging.getLogger('tstools')


class YATSMLandsatPALSARTS(YATSMTimeSeries):
    """ Timeseries driver for Timeseries of Landsat/PALSAR timeseries

    Requires a working installation of YATSM. For more information, visit
    the [YATSM Github website](https://github.com/ceholden/yatsm).

    This driver requires the following Python packages in addition to basic
    TSTools package dependencies:

    * [`scikit-learn`](http://scikit-learn.org/stable/)
    * [`patsy`](https://patsy.readthedocs.org/en/latest/)
    * [`yatsm`](https://github.com/ceholden/yatsm)
    """
    description = 'YATSM Landsat/PALSAR'
    location = None
    mask_values = np.array([2, 3, 4, 255])

    # Driver configuration
    config = YATSMTimeSeries.config.copy()
    config['ps_dir'] = ConfigItem('PALSAR data dir', 'ALOS')
    config['hh_stack_pattern'] = ConfigItem('PALSAR HH image pattern',
                                            '*HH.tif')
    config['vrt_stack_pattern'] = ConfigItem('PALSAR stacked VRT image pattern',
                                              '*stack.vrt')
    config['ps_date_index'] = ConfigItem('PALSAR date index', [9, 17])
    config['ps_date_format'] = ConfigItem('PALSAR date format', '%Y%m%d')

    # redefined
    config['cache_folder'] = ConfigItem('Cache folder', 'cache_fusion')
    config['mask_band'] = ConfigItem('Mask band(s)', [8, 0, 0])

    def __init__(self, location, config=None):
        super(YATSMLandsatPALSARTS, self).__init__(location, config=config)

        # Change name of first series
        self.series[0].description = 'Landsat Timeseries'

        # Add series for RADAR HH/HV/ratio
        self._find_radar()

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
        for progress in super(YATSMLandsatPALSARTS, self).fetch_data(
                mx, my, crs_wkt):
            yield progress

    def _find_radar(self):
        """ Find RADAR images and initialize series
        """
        location = os.path.join(self.location, self.config['ps_dir'].value)

        # Ignore results folder and cache, if we have it
        ignore_dirs = []
        if 'cache_folder' in self.config:
            ignore_dirs.append(self.config['cache_folder'].value)
        if 'results_folder' in self.config:
            ignore_dirs.append(self.config['results_folder'].value)

        # Find HH images
        hh_images = find_files(
            location,
            self.config['hh_stack_pattern'].value,
            ignore_dirs=ignore_dirs)
        if not hh_images:
            raise Exception('Could not find any HH images (*hh.*tif)')
        self.series.append(Series(
            hh_images,
            self.config['ps_date_index'].value,
            self.config['ps_date_format'].value,
            {
                'description': 'PALSAR HH Timeseries',
                'symbology_hint_indices': [0],
                'symbology_hint_minmax': [-20, -2],
                'band_names': ['HH']
            }
        ))

        # Find HH/HV/Ratio VRT images
        vrt_images = find_files(
            location,
            self.config['vrt_stack_pattern'].value,
            ignore_dirs=ignore_dirs)
        if not vrt_images:
            raise Exception('Could not find any HH/HV/Ratio images (*.vrt)')
        self.series.append(Series(
            vrt_images,
            self.config['ps_date_index'].value,
            self.config['ps_date_format'].value,
            {
                'description': 'PALSAR HH/HV/Ratio Timeseries',
                'symbology_hint_indices': [0, 1, 2],
                'symbology_hint_minmax': [
                    (-20.0, -25.0, 3.0),
                    (-2.0, -10.0, 11.0)
                ],
                'band_names': ['HH', 'HV', 'HH/HV']
            }
        ))
