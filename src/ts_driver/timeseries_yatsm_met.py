""" Timeseries driver for Landsat timeseries with meteorological data
"""
import logging
import os

from . import ts_utils
from .series import Series
from .timeseries_yatsm import YATSMTimeSeries

logger = logging.getLogger('tstools')


class YATSMMetTimeSeries(YATSMTimeSeries):
    description = 'YATSM CCDCesque Timeseries + Met'
    location = None

    _met_location = 'PRISM'
    _met_types = ['ppt', 'tmin', 'tmax', 'tmean']
    _met_pattern = 'PRISM*.bil'
    _met_date_index = [23, 29]
    _met_date_format = '%Y%m'

    config = [c for c in YATSMTimeSeries.config]
    config.extend([
        '_met_location', '_met_types', '_met_pattern',
        '_met_date_index', '_met_date_format',
    ])
    config_names = [cn for cn in YATSMTimeSeries.config_names]
    config_names.extend([
        'Met root location', 'Met types', 'Met data pattern',
        'Met date index', 'Met date format',
    ])

    def __init__(self, location, config=None):
        super(YATSMMetTimeSeries, self).__init__(location, config=config)

        min_max_symbology = {
            'ppt': [0, 300],
        }

        for met_type in self._met_types:
            logger.debug('Finding met data: %s' % met_type)
            images = ts_utils.find_files(
                os.path.join(self._met_location, met_type),
                self._met_pattern)
            series = Series(
                images,
                self._met_date_index, self._met_date_format,
                {
                    'description': met_type,
                    'symbology_hint_indices': [0],
                    'cache_prefix': 'met_%s_' % met_type,
                    'cache_suffix': '.npy'
                }
            )
            if met_type in min_max_symbology:
                series.symbology_hint_minmax = min_max_symbology[met_type]
            self.series.append(series)
