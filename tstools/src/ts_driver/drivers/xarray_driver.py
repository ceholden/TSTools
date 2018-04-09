""" Driver for ``xarray``-based access to NetCDF4 files
"""
from collections import OrderedDict, defaultdict
import logging
import os
import tempfile

import numpy as np
from osgeo import gdal

from ..ts_utils import ConfigItem, find_files
from ..timeseries import AbstractTimeSeriesDriver
from ...utils import geo_utils, vrt

# Try to open difficult imports
has_reqs = True
try:
    import xarray as xr
    import dask
except ImportError:
    has_reqs = False

logger = logging.getLogger('tstools')


BANDS = [
    'blue',
    'green',
    'red',
    'nir',
    'swir1',
    'swir2',
    'temp',
    'cfmask'
]


# vrt.VRT helpers
def filter_subdatasets_by_band(files, bands):
    """ Return a collection of subdatasets per file containing all band SDS

    Parameters
    ----------
    files : list[str]
        File path locations
    bands : list[str]
        Band names to include

    Returns
    -------
    dict[str, list[GDALDataset]]
        Band names (variables) to NetCDF variable datasets
    """
    out = defaultdict(list)
    for f in files:
        ds = gdal.Open(f)
        for sds, desc in ds.GetSubDatasets():
            band_name = sds.split(':')[-1].strip()
            if band_name in bands:
                out[band_name].append(sds)
    return out


def collect_bands_across_datasets(datasets, bands):
    """ Collect references to (dataset, bidx) for all obs for all bands

    Parameters
    ----------
    datasets : dict[str, list[GDALDataset]]
        Band names (variables) to NetCDF variable datasets
    bands : list[str]
        Band names to include

    Returns
    -------
    dict[int, list[GDALDAtaset, int]]
        Mapping of time index to GDAL dataset and band index number
    """
    out = defaultdict(list)
    for b in bands:
        for ds in datasets[b]:
            _ds = gdal.Open(ds)
            for bidx in range(_ds.RasterCount):
                out[bidx].append((_ds, bidx + 1))
    return out


# SERIES
class XarraySeries(object):
    description = 'Xarray Time Series'
    images = np.empty(
        0,
        dtype=[
            ('filename', object),
            ('path', object),
            ('id', object),
            ('date', object),
            ('ordinal', 'u4'),
            ('doy', 'u2')
        ]
    )
    band_names = []

    x_dim = 'x'
    y_dim = 'y'
    time_dim = 'time'

    symbology_hint_indices = [3, 2, 1]
    symbology_hint_minmax = [0, 10000]

    def __init__(self, filenames, ncvars, config=None):
        if config:
            self.__dict__.update(config)
        self.filenames = filenames
        self.band_names = ncvars

        # Read in NetCDF4 files as multiple dataset
        # TODO chunks
        logger.info('Opening NetCDFs with xarray. Be patient...')
        self.ds = xr.open_mfdataset(
            filenames,
            chunks={
                self.x_dim: 250,
                self.y_dim: 250,
                self.time_dim: 250
            },
            concat_dim=self.time_dim
        )
        logger.info('Done!')

        # Create VRTs
        self._init_vrts()

        # Setup series
        self._init_attributes(self.ds)

    def fetch_data(self, mx, my, crs_wkt, **kwargs):
        """ Read data for a gixen X/Y coordinate in a given CRS
        """
        pass

    def _init_vrts(self):
        """ Creates temporary VRTs for use in plugin
        """
        self.tmpdir = tempfile.mkdtemp(prefix='TSTools', suffix='xarray')

        subdatasets = filter_subdatasets_by_band(self.filenames,
                                                 self.band_names)
        sds_bidx = collect_bands_across_datasets(subdatasets,
                                                 self.band_names)
        # Iterate over all timestamps, creating VRTs
        logger.info('Creating VRTs to use with xarray')
        for k in sds_bidx:
            vrt_ = vrt.VRT(*zip(*sds_bidx[k]))
            vrt_.write(os.path.join(self.tmpdir, str(k) + '.vrt'))

    def _init_attributes(self, ds):
        self.n = ds.time.size
        if self.n == 0:
            raise Exception('Cannot initialize a Series of 0 images')
        # gt and crs from non-CF backup attrs used by GDAL
        self.gt = ds.crs.attrs['GeoTransform']
        self.crs = ds.crs.attrs['spatial_ref']

        _images = np.empty(self.n, dtype=self.images.dtype)
        dates = self.ds['time'].to_index()
        for i, date_ in enumerate(dates):
            # Filename constructed as '1.vrt', ..., 'n.vrt' according to
            # order in time dimension
            _images[i]['filename'] = str(i)
            _images[i]['path'] = os.path.join(self.tmpdir, str(i) + '.vrt')
            # issue is we have no guarenteed metadata here, like an 'id'
            # ... unless we specified "id_var"? TODO
            _images[i]['id'] = date_.strftime('%Y-%m-%d')
            _images[i]['date'] = date_.date()
            _images[i]['ordinal'] = date_.toordinal()
            _images[i]['doy'] = int(date_.strftime('%j'))

        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]

        self.images = _images.copy()


# DRIVER
class XarrayDriver(AbstractTimeSeriesDriver):
    """ Time series driver for xarray

    Requires the following extra set of Python dependencies:
        - dask
        - xarray
    """
    description = 'Xarray NetCDF Reader'
    location = None
    config = OrderedDict((
        ('nc_pattern', ConfigItem('NetCDF pattern', 'L*.nc')),
        ('vars', ConfigItem('Data Variables', BANDS)),
        ('mask_var', ConfigItem('Mask variable', ['cfmask'])),
        ('x_dim', ConfigItem('X dim name', 'x')),
        ('y_dim', ConfigItem('Y dim name', 'y')),
    ))
    series = []
    mask_values = np.array([2, 3, 4, 255])
    pixel_pos = ''
    has_results = False

    def __init__(self, location, config=None):
        if not has_reqs:
            raise ImportError('Cannot use {0.__class__.__name__} without '
                              'xarray/dask'.format(self))
        super(XarrayDriver, self).__init__(location, config=config)
        self.x_dim = self.config['x_dim'].value
        self.y_dim = self.config['y_dim'].value
        self.mask_var = self.config['mask_var'].value

        ncdfs = find_files(self.location, self.config['nc_pattern'].value)

        cfg = {
            'x_dim': self.x_dim,
            'y_dim': self.y_dim
        }
        series_ = XarraySeries(ncdfs, self.config['vars'].value, config=cfg)

        self.series = [series_]
        self.da = []

    def fetch_data(self, mx, my, crs_wkt):
        self.da = []
        n = len(self.series)
        for i, series in enumerate(self.series):
            # TODO: I think xarray can handle this...
            _mx, _my = geo_utils.reproject_point(mx, my, crs_wkt, series.crs)
            _px, _py = geo_utils.point2pixel(_mx, _my, series.gt)

            self.pixel_pos = 'Row/Col: {}/{}'.format(_py, _px)

            # Actually do the read...
            sel = {
                self.x_dim: _mx,
                self.y_dim: _my
            }
            da = (series.ds[series.band_names]
                  .sel(method='nearest', **sel)
                  .to_array('band')
                  .compute())
            self.da.append(da)
            self.px, self.py = _px, _py
            yield 99. * float(i + 1) / float(n)

        self.update_mask(self.mask_values)
        yield 100

    def get_data(self, series, band, mask=True, indices=None):
        if not self.da:
            return (self.series[series].images,
                    np.zeros(self.series[series].images.shape[0]))

        x = self.series[series].images
        y = self.da[series].data.take(band, axis=0)

        if mask is True:
            mask = np.where(self.series[series].mask)[0]

        if isinstance(indices, np.ndarray):
            if isinstance(mask, np.ndarray):
                mask = indices[np.in1d(indices, mask)]
            else:
                mask = indices

        if mask is not False:
            x = x.take(mask, axis=0)
            y = y.take(mask, axis=0)

        return x, y

    def update_mask(self, mask_values=None):
        if mask_values is not None:
            self.mask_values = np.asarray(mask_values).copy()

        for idx, (mask_var, series) in enumerate(
                zip(self.config['mask_var'].value, self.series)):
            if mask_values is None:
                continue
            mask_var = self.config['mask_var'].value
            bands = self.da[idx].band.values
            if mask_var not in bands:
                logger.warning('Cannot apply mask because it does not exist '
                               'retrieved dataset (bands {bands})'.format(
                                   bands=', '.join('"%s"' % b for b in bands)))
            mask = self.da[idx].sel(band=mask_var).data
            series.mask = np.in1d(mask, self.mask_values, invert=True)

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
