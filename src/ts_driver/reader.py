import numpy as np
from osgeo import gdal, gdal_array

gdal.AllRegister()
gdal.UseExceptions()


class _GDALStackReader(object):
    """ Simple class to read stacks using GDAL, keeping file objects open

    Some tests have shown that we can speed up total dataset read time by
    storing the file object references to each image as we loop over many rows
    instead of opening once per row read. This is a simple class designed to
    store these references.

    Note that this class assumes the images are "stacked" -- that is that all
    images contain the same number of rows, columns, and bands, and the images
    are of the same geographic extent.

    Args:
      filenames (list): list of filenames to read from

    Attributes:
      filenames (list): list of filenames to read from
      n_image (int): number of images
      n_band (int): number of bands in an image
      n_col (int): number of columns per row
      datatype (np.dtype): NumPy datatype of images
      datasets (list): list of GDAL datasets for all filenames
      dataset_bands (list): list of lists containing all GDAL raster band
        datasets, for all image filenames

    """
    def __init__(self, filenames):
        self.filenames = filenames

        self.datasets = []
        for f in self.filenames:
            self.datasets.append(gdal.Open(f, gdal.GA_ReadOnly))

        self.n_image = len(filenames)
        self.n_band = self.datasets[0].RasterCount
        self.n_col = self.datasets[0].RasterXSize
        self.datatype = gdal_array.GDALTypeCodeToNumericTypeCode(
            self.datasets[0].GetRasterBand(1).DataType)

        self.dataset_bands = []
        for ds in self.datasets:
            bands = []
            for i in xrange(self.n_band):
                bands.append(ds.GetRasterBand(i + 1))
            self.dataset_bands.append(bands)

        self.dataset_bands = np.asarray(self.dataset_bands)

    def read_pix(self, x, y, i):
        """ Return a 1D NumPy array (nband) of one pixel's data from one image

        Args:
          x (int): column
          y (int): row
          i (int): index of timeseries image to read

        Returns:
          np.ndarray: 1D NumPy array (nband) of image data for desired pixel

        """
        data = np.empty((self.n_band), self.datatype)
        for n_b, band in enumerate(self.dataset_bands[i]):
            data[n_b] = band.ReadAsArray(x, y, 1, 1)

        return data

    def read_pix_ts(self, x, y):
        """ Return a 2D NumPy array (nband x nimage) of one pixel's data

        Args:
          x (int): column
          y (int): row

        Returns:
          np.ndarray: 2D NumPy array (nband x nimage) of image data for desired
            pixel

        """
        data = np.empty((self.n_band, self.n_image), self.datatype)
        for i, ds_bands in enumerate(self.dataset_bands):
            for n_b, band in enumerate(ds_bands):
                data[n_b, i] = band.ReadAsArray(x, y, 1, 1)

        return data


_gdal_stack_reader = None
def read_pixel_GDAL(filenames, x, y, i=None):
    """ Reads in a pixel of data from one or more images using GDAL

    Args:
      filenames (iterable): sequence of filenames to read from
      x (int): column
      y (int): row
      i (int): index of timeseries image to read

    Returns:
      np.ndarray: 1D (nband) or 2D array (nband x nimage) containing the pixel
        data

    """
    global _gdal_stack_reader
    if _gdal_stack_reader is None or \
            not np.array_equal(_gdal_stack_reader.filenames, filenames):
        _gdal_stack_reader = _GDALStackReader(filenames)

    if i is not None:
        return _gdal_stack_reader.read_pix(x, y, i)
    else:
        return _gdal_stack_reader.read_pix_ts(x, y)
