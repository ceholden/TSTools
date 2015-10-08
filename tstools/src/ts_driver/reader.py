""" Functions and classes useful for reading remote sensing imagery in GDAL
"""
import logging

import numpy as np
from osgeo import gdal, gdal_array

logger = logging.getLogger('tstools')

gdal.AllRegister()
gdal.UseExceptions()


def read_pixel_GDAL(filename, x, y):
    """ Reads in a pixel of data from an images using GDAL

    Args:
      filename (str): filename to read from
      x (int): column
      y (int): row

    Returns:
      np.ndarray: 1D array (nband) containing the pixel data

    """
    ds = gdal.Open(filename, gdal.GA_ReadOnly)
    dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
        ds.GetRasterBand(1).DataType)

    dat = np.empty(ds.RasterCount, dtype=dtype)
    for i in range(ds.RasterCount):
        dat[i] = ds.GetRasterBand(i + 1).ReadAsArray(x, y, 1, 1)

    return dat
