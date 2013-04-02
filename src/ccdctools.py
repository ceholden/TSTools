# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCTools
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint

# Initialize Qt resources from file resources.py
import resources_rc

from ccdc_controller import Controller
from ccdc_controls import CCDCControls
from ccdc_plot import CCDCPlot
from ccdc_timeseries import CCDCTimeSeries

class CCDCTools:

    def __init__(self, iface):
        ### Optional stuff to move elsewhere... #TODO
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        self.click_tool = QgsMapToolEmitPoint(self.canvas)
        self.canvas.setMapTool(self.click_tool) #TODO don't have this here

        ### Location info - define these elsewhere
        self.location = '/home/ceholden/Dropbox/Work/Research/pyCCDC/Dataset/p012r031/images'
		self.image_pattern = 'LND*'
        self.stack_pattern = '*stack'
       
    def init_controls(self):
        """
        Initialize and add signals to the left side control widget
        """
        
        print 'init_controls'
        
        # Create widget
        self.ctrl_widget = CCDCControls(self.iface)
        # Create dock and add control widget
        self.ctrl_dock = QDockWidget("CCDC Tools", self.iface.mainWindow())
        self.ctrl_dock.setObjectName("CCDC Tools")
        self.ctrl_dock.setWidget(self.ctrl_widget)
        # Connect signals #TODO
        # Add to iface
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.ctrl_dock)

    def init_plotter(self):
        """
        Initialize and add signals to the bottom area plotting widget
        """
        # Create widget
        self.plot_widget = CCDCPlot(self.iface)
        # Create dock and add plot widget
        self.plot_dock = QDockWidget('CCDC Plot', self.iface.mainWindow())
        self.plot_dock.setObjectName('CCDC Plot')
        self.plot_dock.setWidget(self.plot_widget)
        # Connect signals #TODO
        # Add to iface
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.plot_dock)

    def initGui(self):
        """
        Required method for Qt to load components. Also inits signal controller
        """
        self.init_controls()

        self.init_plotter()
        self.controller = Controller(self.ctrl_widget, self.plot_widget)
        self.controller.get_time_series(self.location, 
                                        self.image_pattern,
                                        self.stack_pattern)
        QObject.connect(self.click_tool,
                    SIGNAL('canvasClicked(const QgsPoint &, Qt::MouseButton)'),
                    self.plot_request)
    
    def plot_request(self, pos, button=None):
        print 'Trying to fetch...'
        if self.canvas.layerCount() == 0 or pos is None:
            print 'Could not fetch...'
            return
        layer = self.canvas.currentLayer()
        if (layer == None or layer.isValid() == False or 
            layer.type() != QgsMapLayer.RasterLayer):
            print 'Invalid layer...'
            return

        # Check if position needs to be reprojected to layer CRS
        if QGis.QGIS_VERSION_INT >= 10900:
            layerCrs = layer.crs()
            mapCrs = self.canvas.mapRenderer().destinationCrs()
        else:
            layerCrs = layer.srs()
            mapCrs = self.canvas.mapRenderer().destinationSrs()

        if not mapCrs == layerCrs and self.canvas.hasCrsTransformEnabled():
            crsTransform = QgsCoordinateTransform(mapCrs, layerCrs)
            try:
                pos = crsTransform.transform(pos)
            except QgsCsException, err:
                print 'Transformation error'
                pass #TODO handle better?

        # If layer has position, get data
        if layer and layer.extent().contains(pos):
            self.controller.fetch_data(pos)
            self.controller.update_display()

    def unload(self):
        """
        Handle startup/shutdown/hide/etc behavior
        """
        # Close dock & disconnect widget
        self.ctrl_dock.close()
        self.plot_widget.disconnect()
        self.ctrl_dock.close()
        self.plot_dock.close()
