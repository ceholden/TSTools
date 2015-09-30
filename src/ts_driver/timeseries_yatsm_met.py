""" Timeseries driver for Landsat timeseries with meteorological data
"""
import datetime as dt
import logging
import os

from . import ts_utils
from .series import Series
from .timeseries_yatsm import YATSMTimeSeries
from ..logger import qgis_log

logger = logging.getLogger('tstools')


class YATSMMetTimeSeries(YATSMTimeSeries):
    description = 'YATSM CCDCesque Timeseries + Met'
    location = None

    _met_location = 'PRISM'
    _met_types = ['ppt', 'tmin', 'tmax', 'tmean']
    _met_pattern = 'PRISM*.bil'
    _met_date_sep = '_'
    _met_date_sepno = 4
    _met_date_format = '%Y%m'

    config = [c for c in YATSMTimeSeries.config]
    config.extend([
        '_met_location', '_met_types', '_met_pattern',
        '_met_date_sep', '_met_date_sepno', '_met_date_format'
    ])
    config_names = [cn for cn in YATSMTimeSeries.config_names]
    config_names.extend([
        'Met root location', 'Met types', 'Met data pattern',
        'Met filename separator', 'Met date index', 'Met date format'
    ])

    def __init__(self, location, config=None):
        super(YATSMMetTimeSeries, self).__init__(location, config=config)

        min_max_symbology = {
            'ppt': [0, 300],
            'tmin': [-30, 35],
            'tmean': [-30, 35],
            'tmax': [-30, 35]
        }

        for met_type in self._met_types:
            logger.debug('Finding met data: %s' % met_type)
            images = ts_utils.find_files(
                os.path.join(self._met_location, met_type),
                self._met_pattern)

            # Get date index from file
            img = os.path.basename(images[0])
            d = img.split(self._met_date_sep)[self._met_date_sepno]
            try:
                dt.datetime.strptime(d, self._met_date_format)
            except Exception as e:
                qgis_log('Could not parse date from %ith "%s"-separated field '
                         'of filename %s using date format %s: %s' %
                         (self._met_date_sepno, self._met_date_sep,
                          img, self._met_date_format, e.message))
                raise
            idx_start = img.find(d)
            self._met_date_index = (idx_start, idx_start + len(d))

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
