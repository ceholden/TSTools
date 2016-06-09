""" Driver for AGDC v2
"""
from collections import OrderedDict

import numpy as np

from .agdc_series import AGDCSeries
from ...ts_utils import ConfigItem, find_files
from ...timeseries import AbstractTimeSeriesDriver
from ....utils import geo_utils

# Try to open difficult imports
has_reqs = True
try:
    import xarray as xr
    import dask
except ImportError:
    has_reqs = False


BANDS = ['band1', 'band2', 'band3', 'band4', 'band5', 'band7',
         'cfmask']  # NOTE: no temperature "band6"



class AGDCTimeSeriesDriver(AbstractTimeSeriesDriver):
    """ Time series driver for AGDC v2

    Requires the following extra set of Python dependencies:
        - dask
        - xarray
        - NetCDF4
    """
    description = 'AGDC v2 Reader'
    location = None
    config = OrderedDict((
        ('nc_pattern', ConfigItem('NetCDF pattern', 'L*.nc')),
        ('vars', ConfigItem('Data Variables', BANDS))
    ))
    series = []
    mask_values = np.array([2, 3, 4, 255])
    pixel_pos = ''
    has_results = False

    def __init__(self, location, config=None):
        if not has_reqs:
            raise ImportError('Cannot use {0.__class__.__name__} without '
                              'xarray/dask'.format(self))
        super(AGDCTimeSeriesDriver, self).__init__(location, config=config)

        ncdfs = find_files(self.location, self.config['nc_pattern'].value)

        self.series = [
            AGDCSeries(ncdfs, self.config['vars'].value)
        ]
        self.da = None

    def fetch_data(self, mx, my, crs_wkt):
        for series in self.series:
            # TODO: I think xarray can handle this...
            _mx, _my = geo_utils.reproject_point(mx, my, crs_wkt, series.crs)
            _px, _py = geo_utils.point2pixel(_mx, _my, series.gt)

            self.pixel_pos = 'Row/Col: {}/{}'.format(_py, _px)

            # Actually do the read...
            self.da = (series.ds[series.band_names]
                        .sel(latitude=_my, longitude=_mx, method='nearest')
                        .load().to_array())
            self.px, self.py = _px, _py
        yield 100.0

    def get_data(self, series, band, mask=True, indices=None):
        if self.da is None:
            return (self.series[series].images,
                    np.zeros(self.series[series].images.shape[0]))
        # TODO: not masking as of yet...
        x = self.series[series].images
        y = self.da.data.take(band, axis=0)

        return x, y

    def update_mask(sefl, mask_values=None):
        pass

    def get_geometry(self):
        geom = geo_utils.pixel_geometry(self.series[0].gt, self.px, self.py)
        return geom.ExportToWkt(), self.series[0].crs

# NOT IMPLEMENTED
    def fetch_results(self):
        pass

    def get_prediction(self, series, band, dates=None):
        pass

    def get_breaks(self, series, band):
        pass

    def get_residuals(self, series, band):
        pass
