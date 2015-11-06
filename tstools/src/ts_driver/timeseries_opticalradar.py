""" A driver for running YATSM on stacked Landsat/PALSAR timeseries
"""
from datetime import datetime as dt
import logging
import os

import numpy as np
import patsy

from .timeseries import Series
from .timeseries_yatsm import YATSMTimeSeries
from .ts_utils import find_files, parse_landsat_MTL

logger = logging.getLogger('tstools')


class YATSMLandsatPALSARTS(YATSMTimeSeries):

    """ Timeseries driver for Timeseries of Landsat/PALSAR timeseries
    """
    description = 'YATSM Landsat/PALSAR'
    location = None
    mask_values = np.array([2, 3, 4, 255])

    # Driver configuration
    _ps_dir = 'RADAR'
    _ps_stack_pattern = '*ALPSRP*'
    _ps_date_index = [8, 16]
    _cache_folder = 'cache_fusion'  # redefined
    _mask_band = [8, 0, 0]  # redefined

    config = [c for c in YATSMTimeSeries.config]
    config.extend([
        '_ps_dir',
        '_ps_stack_pattern',
        '_ps_date_index'
    ])
    config_names = [cn for cn in YATSMTimeSeries.config_names]
    config_names.extend([
        'PALSAR data directory',
        'PALSAR stack pattern',
        'PALSAR date index'
    ])

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

        # Convert RADAR DNs to dB: dB = ( DN - 1 ) * 0.15 - 31.0
        for series in self.series[1:]:
            if series.data is None:
                continue
            logger.debug('Rescaling %s to dB' % (series.description, ))
            logger.debug(series.data.shape)
            series.data[0, :] = (series.data[0, :] - 1) * 0.15 - 31.0
            if series.data.shape[0] > 1:
                series.data[1, :] = (series.data[1, :] - 1) * 0.15 - 31.0
                series.data[2, :] = series.data[0, :] / series.data[1, :]
            logger.debug('Rescaled. Data min/max: {0}/{1}'.format(
                         series.data.min(axis=1), series.data.max(axis=1)))

    def _find_radar(self):
        """ Find RADAR images and initialize series
        """
        location = os.path.join(self.location, self._ps_dir)

        # Ignore results folder and cache, if we have it
        ignore_dirs = []
        if hasattr(self, '_cache_folder'):
            ignore_dirs.append(getattr(self, '_cache_folder'))
        if hasattr(self, '_results_folder'):
            ignore_dirs.append(getattr(self, '_results_folder'))

        # Find HH images
        hh_images = find_files(location, self._ps_stack_pattern + '*hh.gtif',
                               ignore_dirs=ignore_dirs)
        if not hh_images:
            raise Exception('Could not find any HH images (*hh.gtif)')
        self.series.append(Series(
            hh_images, self._ps_date_index, '%Y%m%d',
            {
                'description': 'PALSAR HH Timeseries',
                'symbology_hint_indices': [0],
                'symbology_hint_minmax': [0, 255],
                'band_names': ['HH']
            }
        ))

        # Find HH/HV/Ratio VRT images
        vrt_images = find_files(location, self._ps_stack_pattern + '*.vrt',
                                ignore_dirs=ignore_dirs)
        if not vrt_images:
            raise Exception('Could not find any HH/HV/Ratio images (*.vrt)')
        self.series.append(Series(
            vrt_images, self._ps_date_index, '%Y%m%d',
            {
                'description': 'PALSAR HH/HV/Ratio Timeseries',
                'symbology_hint_indices': [0, 1, 2],
                'symbology_hint_minmax': [0, 255],
                'band_names': ['HH', 'HV', 'HH/HV']
            }
        ))
