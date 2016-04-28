""" Timeseries driver for Landsat timeseries with meteorological data
"""
import datetime as dt
import logging
import os

from .timeseries_yatsm import YATSMTimeSeries
from ..ts_utils import ConfigItem, find_files
from ..series import Series
from ...logger import qgis_log

logger = logging.getLogger('tstools')


class YATSMMetTimeSeries(YATSMTimeSeries):
    description = 'YATSM CCDCesque Timeseries + Met'
    location = None

    config = YATSMTimeSeries.config.copy()
    config['met_location'] = ConfigItem('Met root location', 'PRISM')
    config['met_types'] = ConfigItem('Met types',
                                     ['ppt', 'tmin', 'tmax', 'tmean'])
    config['met_pattern'] = ConfigItem('Met data pattern', 'PRISM*.bil')
    config['met_date_sep'] = ConfigItem('Met filename separator', '_')
    config['met_date_sepno'] = ConfigItem('Met date index', 4)
    config['met_date_format'] = ConfigItem('Met date format', '%Y%m')

    def __init__(self, location, config=None):
        super(YATSMMetTimeSeries, self).__init__(location, config=config)

        min_max_symbology = {
            'ppt': [0, 300],
            'tmin': [-30, 35],
            'tmean': [-30, 35],
            'tmax': [-30, 35]
        }

        for met_type in self.config['met_types'].value:
            logger.debug('Finding met data: %s' % met_type)
            images = find_files(
                os.path.join(self.config['met_location'].value, met_type),
                self.config['met_pattern'].value)

            # Get date index from file
            img = os.path.splitext(os.path.basename(images[0]))[0]
            d = img.split(self.config['met_date_sep'].value)[
                self.config['met_date_sepno'].value]
            try:
                dt.datetime.strptime(d, self._met_date_format)
            except Exception as e:
                qgis_log('Could not parse date from %ith "%s"-separated field '
                         'of filename %s using date format %s: %s' %
                         (self.config['met_date_sepno'].value,
                          self.config['met_date_sep'].value,
                          img,
                          self.config['met_date_format'].value,
                          e.message))
                raise
            idx_start = img.find(d)
            self._met_date_index = (idx_start, idx_start + len(d))

            series = Series(
                images,
                self.config['met_date_index'].value,
                self.config['met_date_format'].value,
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
