# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
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

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg

import numpy as np

import datetime
import fnmatch
import os

from ccdc_timeseries import CCDCTimeSeries
from ui_ccdctools import Ui_CCDCTools as Ui_Widget


class CCDCWidget(QWidget, Ui_Widget):
    
    def __init__(self, iface):
        # Location info - define these elsewhere
        stack_dir = '/home/ceholden/Dropbox/Work/Research/pyCCDC/Dataset/p012r031/images'
		# stack_dir = '/net/casfsc/fs/scratch24/ceholden/p013r031/images'
		#stack_dir = '/net/caseq/lcscratch/ceholden/p012r030/images'
		image_pattern = 'LND*'
        stack_pattern = '*stack'

		### Default options
		# Show/do not show plot
		self.show_plot = False
		# Enable/disable selection tool
		self.select_tool = False
        # Initial band selection
        self.band_select = 0
		# Use mask?
		self.fmask = True

		### Data
        # Load the time series object
        self.ts = CCDCTimeSeries(stack_dir, image_pattern, stack_pattern)
        # Initialize dataset to plot
        self.y = self.ts.data
        self.x = np.arange(self.ts.length)
		self.reccg = []

        ### Qt interface elements
		# Grab & store interface components
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        QWidget.__init__(self)
		# Custom setup of UI
        self.setupUi(self)
		# Initialize the matplotlib graph
        self.setup_plots()
        
		### User interaction
		self.setup_controls()

    def setup_controls(self):
        # Plot on/off checkbox
		if self.show_plot:
            self.cbox_active.setCheckState(Qt.Checked)
		QObject.connect(self.cbox_active,
			SIGNAL('stateChanged(int)'), self.set_active)

		# Checkbox for tool
		self.click_tool = QgsMapToolEmitPoint(self.canvas)
		# TODO: move this to a button in the toolbar
		if self.select_tool:
			self.cbox_tool.setCheckState(Qt.Checked)
		QObject.connect(self.cbox_tool,
			SIGNAL('stateChanged(int)'), self.set_tool)

		# Setup for Fmask checkbox
		if self.fmask:
			self.cbox_fmask.setCheckState(Qt.Checked)
		QObject.connect(self.cbox_fmask,
			SIGNAL('stateChanged(int)'), self.set_fmask)

		# Setup raster band select QComboBox
		self.combox_band_select.addItems(self.ts.band_names)   
		self.combox_band_select.setCurrentIndex(0)
		QObject.connect(self.combox_band_select,
			SIGNAL('currentIndexChanged(int)'), self.set_band_select)
 
    def setup_plots(self):
        # matplotlib
        self.mplFig = plt.Figure(facecolor = 'w', edgecolor = 'w')
        self.mplPlt = self.mplFig.add_subplot(111)
        self.mplPlt.tick_params(axis = 'y', which = 'minor', labelsize=12)
        self.mplPlt.tick_params(axis = 'y', which = 'major', labelsize=10)
        self.mplPlt.set_ylim([0, 10000])
        # Setup matplotlib to add to Qt element
        self.pltCanvas = FigureCanvasQTAgg(self.mplFig)
        self.pltCanvas.setParent(self.stackedWidget)
        self.pltCanvas.setAutoFillBackground(False)
        self.pltCanvas.setObjectName('mplPlot')
        self.mplPlot = self.pltCanvas
        self.mplPlot.setVisible(True)
        # Configure aspect resizing policy
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.mplPlot.sizePolicy().hasHeightForWidth())
        self.mplPlot.setSizePolicy(sizePolicy)
        self.mplPlot.updateGeometry()
        self.stackedWidget.addWidget(self.mplPlot)
        
        self.stackedWidget.setCurrentIndex(0)
    
    def fetch_data(self, pos, button=None ):
        print 'Trying to fetch...'
        ### Return if no layers active or no coordinates
        if self.canvas.layerCount() == 0 or pos is None:
            print 'Could not fetch...'
            return
        ### If not... grab the values
        layer = self.canvas.currentLayer()
        # Make sure layer is not None and is a raster
        if (layer == None or layer.isValid() == False or 
            layer.type() != QgsMapLayer.RasterLayer):
            print 'Layer invalid'
            return
            
        ### Check if position needs to be transformed to layer CRS
        # Layer & canvas CRS
        if QGis.QGIS_VERSION_INT >= 10900:
            layerCrs = layer.crs()
            mapCrs = self.canvas.mapRenderer().destinationCrs()
        else:
            layerCrs = layer.srs()
            mapCrs = self.canvas.mapRenderer().destinationSrs()
        # Check if they're the same...
        print 'CRS map == layer: %s' % str(mapCrs == layerCrs)
        if not mapCrs == layerCrs and self.canvas.hasCrsTransformEnabled():
            crsTransform = QgsCoordinateTransform(mapCrs, layerCrs)
            try:
                pos = crsTransform.transform(pos)
            except QgsCsException, err:
                print 'Transformation error'
                pass
        # Make sure layer contains the point before we get data
        if layer and layer.extent().contains(pos):
            px = int((pos[0] - self.ts.geo_transform[0]) / 
                self.ts.geo_transform[1])
            py = int((pos[1] - self.ts.geo_transform[3]) /
                self.ts.geo_transform[5])    
            print 'Pixel x/y %s/%s' % (px, py)
            self.y = self.ts.get_ts_pixel(px, py, mask=self.fmask)
			self.reccg = self.ts.get_reccg_pixel(px, py)
			print str(len(self.reccg))
			self.plot()
			
 
    def plot(self):
        # The actual plotting...
        self.mplPlt.clear()
#       self.mplPlt.set_ylim([0, 10000])
#		self.mplPlt.set_ylim([np.min(self.y[self.band_select, ]),
#			np.max(self.y[self.band_select, ])])
        self.mplPlt.plot(self.x, self.y[self.band_select, ], 
            marker='o', ls='', color='r')
#        self.mplPlt.set_xticks(range(len(self.x)))
#        self.mplPlt.set_xticklabels(self.x)
#        self.mplFig.canvas.draw()

		# CCDC time series fit...
		# TODO: a lot...
		if len(self.reccg) > 0:
			mx = np.linspace(self.reccg[0]['t_start'], self.reccg[-1]['t_end'],
				len(self.x))
			rec = self.reccg[0]
			coef = rec['coefs'][:, self.band_select]
			my = (coef[0] +
				coef[1] * mx +
				coef[2] * np.cos(2 * np.pi / 365 * mx) +
				coef[3] * np.sin(2 * np.pi / 365 * mx))
			self.mplPlt.plot(self.x, my)


#		for rec in self.reccg:
#			mx = np.linspace(rec['t_start'], rec['t_end'], 
#				rec['t_end'] - rec['t_start'])
#			coef = rec['coefs'][:, self.band_select]
#			my = (coef[0] + 
#				coef[1] * mx + 
#				coef[2] * np.cos(2 * np.pi / 365 * mx) +
#				coef[3] * np.sin(2 * np.pi / 365 * mx))
#			self.mplPlt.plot

		self.mplFig.canvas.draw()
    
	def set_tool(self, state):
		if (state == Qt.Checked):
			# Add our own map tool
			self.canvas.setMapTool(self.click_tool)
		elif (state == Qt.Unchecked):
			# Unset our own map tool
			self.canvas.unsetMapTool(self.click_tool)

	def set_fmask(self, state):
		if (state == Qt.Checked):
			self.fmask = True
		elif (state == Qt.Unchecked):
			self.fmask = False
		self.fetch_data()

	def set_band_select(self, index):
		print 'Changed band...'
		print 'Index is %s' % str(index)
		if index >= 0 and index < self.ts.n_band:
			self.band_select = index
			self.plot()

    def disconnect(self):
        self.set_active(False)
        
    def set_active(self, state):
        if (state == Qt.Checked):
            # Handle connecting signals to user events
            result = QObject.connect(self.click_tool, 
                SIGNAL('canvasClicked(const QgsPoint &, Qt::MouseButton)'), 
                self.fetch_data)
        elif (state == Qt.Unchecked):
            # Handle disconnecting signals to user events
            result = QObject.disconnect(self.click_tool, 
                SIGNAL('canvasClicked(const QgsPoint &, Qt::MouseButton)'), 
                self.fetch_data)
