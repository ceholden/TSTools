# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CCDCToolsDialog
                                 A QGIS plugin
 Plotting & visualization tools for CCDC Landsat time series analysis
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@bu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import numpy as np

from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly

class CCDCBinaryReader:
	"""
    This class defines the methods for reading pixel values from a raster
	dataset. I've coded this up because certain file formats are more
	efficiently accessed via fopen than via GDAL (i.e. BIP).

	http://osdir.com/ml/gdal-development-gis-osgeo/2007-04/msg00345.html

	Keyword arguments:
	filename -- the filename of the raster to read from
	fformat -- the file format of the raster
	dt -- numpy datatype
	size -- list of [nrow, ncol]

	"""
	def __init__(self, filename, fformat, dt, size):
		self.filename = filename
		self.fformat = fformat
		self.dt = dt
		self.size = size
		# TODO: make this variable
		self.n_band = 8

		# Switch the actual definition of get_pixel by fformat
		# TODO: reimplement this using class inheritance
		# https://www.youtube.com/watch?v=miGolgp9xq8
		if fformat == 'BIP':
			self.get_pixel = self.__BIP_get_pixel

	def __BIP_get_pixel(self, row, col):
		if row < 0 or row >= self.size[0] or col < 0 or col >= self.size[1]:
			raise ValueError, 'Cannot select row,col %s,%s' % (row, col)
			
		with open(self.filename, 'rb') as f:
			# Skip to location of data in file
			f.seek(self.dt.itemsize * (row * self.size[1] + col) * self.n_band)
			# Read in
			dat = np.fromfile(f, self.dt, count = self.n_band)
			f.close()
			return dat
