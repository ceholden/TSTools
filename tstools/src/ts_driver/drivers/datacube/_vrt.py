""" VRT shim to allow NetCDFs as multiband rasters in QGIS

Source: Taken in large part from `tilezilla.stores.vrt`:
https://github.com/ceholden/tilezilla/blob/master/tilezilla/stores/vrt.py

"""
from collections import defaultdict
import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree, Element, SubElement
from xml.dom import minidom

from osgeo import gdal, gdal_array

COLOR_INTERP = defaultdict(str)
COLOR_INTERP[2] = 'Red'
COLOR_INTERP[1] = 'Green'
COLOR_INTERP[0] = 'Blue'



class VRT(object):
    """ Create a VRT from a band in one or more datasets

    Only inteded right now to assist in visualizing (i.e., in QGIS) with
    multiple `Band`s from one `BaseProduct` within one `Tile`.

    Args:
        datasets (list[gdal.Dataset]): GDAL raster dataset
        bidx (list[int]): Band indices of `datasets` to include
    """
    def __init__(self, datasets, bidx):
        self._validate(datasets)
        # Create root
        self.root = Element('VRTDataset')
        self.root.set('rasterXSize', str(datasets[0].RasterXSize))
        self.root.set('rasterYSize', str(datasets[0].RasterYSize))
        # Add CRS & GeoTransform
        self.crs = self._add_crs(datasets[0])
        self.geotransform = self._add_geotransform(datasets[0])
        # Add bands
        self.bands = []
        for idx, (ds, _bidx) in enumerate(zip(datasets, bidx)):
            self.bands.append(self._add_band(idx, ds, _bidx))

    def write(self, path):
        """ Save VRT XML data to a filename

        Args:
            path (str): Save VRT to this filename
        """
        xmlstr = (minidom.parseString(ET.tostring(self.root))
                  .toprettyxml(indent='    '))
        with open(path, 'w') as fid:
            fid.write(xmlstr)

    def _add_crs(self, ds):
        crs = SubElement(self.root, 'SRS')
        crs.text = ds.GetProjectionRef()

        return crs

    def _add_geotransform(self, ds):
        gt = SubElement(self.root, 'GeoTransform')
        gt.text = ', '.join(map(str, ds.GetGeoTransform()))

        return gt

    def _add_band(self, idx, ds, bidx):
        """ Add a band to VRT

        Args:
            idx (int): Index of band in VRT
            ds (RasterReader): `rasterio` dataset
            bidx (int): Band index of `ds`
        """
        _band = ds.GetRasterBand(bidx)
        _dtype_name = gdal.GetDataTypeName(_band.DataType)

        band = SubElement(self.root, 'VRTRasterBand')
        band.set('dataType', _dtype_name)
        band.set('band', str(idx + 1))
        # Color interpretation
        ci = SubElement(band, 'ColorInterp')
        ci.text = COLOR_INTERP[idx]
        # Add NoDataValue
        if _band.GetNoDataValue() is not None:
            ndv = SubElement(band, 'NoDataValue')
            ndv.text = str(_band.GetNoDataValue())
        # Add SimpleSource
        source = SubElement(band, 'SimpleSource')
        source_path = SubElement(source, 'SourceFilename')
        source_path.text = ds.GetDescription()  # no abspath with NETCDF
        source_band = SubElement(source, 'SourceBand')
        source_band.text = str(bidx)
        source_props = SubElement(source, 'SourceProperties')
        source_props.set('RasterXSize', str(ds.RasterXSize))
        source_props.set('RasterYSize', str(ds.RasterYSize))
        source_props.set('DataType', _dtype_name)
        blocks = _band.GetBlockSize()
        source_props.set('BlockXSize', str(blocks[1]))
        source_props.set('BlockYSize', str(blocks[0]))

        return source

    def _validate(self, datasets):
        # Check size
        width, height = datasets[0].RasterXSize, datasets[0].RasterYSize
        for _ds in datasets:
            if (width, height) != (_ds.RasterXSize, _ds.RasterYSize):
                raise ValueError('All datasets must be the same size')
        # Check projection
        crs = datasets[0].GetProjection()
        for _ds in datasets:
            if crs != _ds.GetProjection():
                raise ValueError('All datasets must have same CRS')
