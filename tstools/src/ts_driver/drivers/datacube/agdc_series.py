""" Module for AGDCSeries dataset container class
"""
from collections import defaultdict
import datetime as dt
import logging
import os
import tempfile

import numpy as np
from osgeo import gdal

has_deps = True
try:
    import dask
    import xarray as xr
except ImportError:
    has_deps = False

from ._vrt import VRT

logger = logging.getLogger('tstools')


def filter_subdatasets_by_band(files, bands):
    """ Return a collection of subdatasets per file containing all band SDS

    This should be replaced by calls to AGDC database
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
    """
    out = defaultdict(list)
    for b in bands:
        for ds in datasets[b]:
            _ds = gdal.Open(ds)
            for bidx in range(_ds.RasterCount):
                _b = _ds.GetRasterBand(bidx + 1)
                timestamp = int(_b.GetMetadata()['NETCDF_DIM_time'])
                out[timestamp].append((_ds, bidx + 1))
    return out


class AGDCSeries(object):
    description = 'Data Cube Time Series'
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

    symbology_hint_indices = [3, 2, 1]
    symbology_hint_minmax = [0, 10000]

    def __init__(self, filenames, ncvars, config=None):
        if config:
            self.__dict__.update(config)
        self.filenames = filenames
        self.band_names = ncvars

        # Read in NetCDF4 files as multiple dataset
        # TODO chunks
        self.ds = xr.open_mfdataset(filenames, chunks=100, concat_dim='time')

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
        self.tmpdir = tempfile.mkdtemp(prefix='TSTools', suffix='AGDC')

        subdatasets = filter_subdatasets_by_band(self.filenames,
                                                 self.band_names)
        sds_bidx = collect_bands_across_datasets(subdatasets,
                                                 self.band_names)
        # Iterate over all timestamps, creating VRTs
        logger.info('Creating VRTs to use with AGDC')
        for k in sds_bidx:
            vrt = VRT(*zip(*sds_bidx[k]))
            vrt.write(os.path.join(self.tmpdir, str(k) + '.vrt'))

    def _init_attributes(self, ds):
        self.n = ds.time.size
        if self.n == 0:
            raise Exception('Cannot initialize a Series of 0 images')
        self.gt = ds.crs.attrs['GeoTransform']
        self.crs = ds.crs.attrs['crs_wkt']

        _images = np.empty(self.n, dtype=self.images.dtype)
        dtime = self.ds['time'].to_index().date
        for i, (_tstamp, _dtime) in enumerate(zip(self.ds['time'], dtime)):
            unix_tstamp = _tstamp.data.astype(np.int64) // 10**9
            # TODO: 'filename' is inaccessible w/o API
            _images[i]['filename'] = str(_tstamp.data)
            _images[i]['path'] = os.path.join(self.tmpdir,
                                              str(unix_tstamp) + '.vrt')
            # TODO: 'id' is inaccessible w/o API
            _images[i]['id'] = str(_tstamp.data)
            _images[i]['date'] = _dtime
            _images[i]['ordinal'] = _dtime.toordinal()
            _images[i]['doy'] = int(_dtime.strftime('%j'))

        sort_idx = np.argsort(_images['ordinal'])
        _images = _images[sort_idx]

        self.images = _images.copy()
