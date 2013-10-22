# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TSTools
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                              -------------------
        begin                : 2013-10-01
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@gmail.com
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
import os

# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint, QgsMessageBar

# Initialize Qt resources from file resources.py
import resources_rc

from Config import Config
from controller import Controller
from controls import ControlPanel
from plot import TSPlot
import settings as setting

class TSTools:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()    

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 
                                  'i18n', 
                                  'tstools_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Location info - define these elsewhere #TODO
        self.location = os.getcwd()
        self.image_pattern = 'LND*'
        self.stack_pattern = '*stack'

        
        # Toolbar
        self.init_toolbar()

    def init_toolbar(self):
        """ Creates and populates the toolbar for plugin """
        # MapTool button
        self.action = QAction(QIcon(':/plugins/tstools/icon.png'),
                              'Time Series Tools', self.iface.mainWindow())
        self.action.triggered.connect(self.set_tool)
        self.iface.addToolBarIcon(self.action)

        # Configuration menu button
        self.action_cfg = QAction(QIcon(':/plugins/tstools/icon.png'),
                                  'Configure', self.iface.mainWindow())
        self.action_cfg.triggered.connect(self.handle_config)
        self.iface.addToolBarIcon(self.action_cfg)

        # Map tool
        self.tool_ts = QgsMapToolEmitPoint(self.canvas)
        self.tool_ts.setAction(self.action)
        self.tool_ts.canvasClicked.connect(self.plot_request)

    def set_tool(self):
        """ Sets the time series tool as current map tool """
        self.canvas.setMapTool(self.tool_ts)

    def handle_config(self):
        """ Handles configuration menu for initializing the time series """
        print 'DEBUG %s : show/hide config' % __file__
        # Init the dialog
        self.config = Config(self, self.location, 
                             self.image_pattern, self.stack_pattern)
        # Connect signals
        self.config.accepted.connect(self.config_accepted)
        self.config.canceled.connect(self.config_closed)
        # Execute & show dialog
        self.config.exec_()

    def config_accepted(self):
        """ Handles 'OK' button from Config dialog and tries to add
        time series
        """
        print 'DEBUG %s : config accepted' % __file__
        # Try new values
        location = str(self.config.location)
        image_pattern = str(self.config.image_pattern)
        stack_pattern = str(self.config.stack_pattern)

        success = self.controller.get_time_series(location,
                                                  image_pattern,
                                                  stack_pattern)
        if success:
            # Accept values
            self.location = location
            self.image_pattern = image_pattern
            self.stack_pattern = stack_pattern
            # Close config
            self.config_closed()
            # Send message
            self.iface.messageBar().pushMessage('Info', 
                                                'Loaded time series',
                                                level=QgsMessageBar.INFO,
                                                duration=3)
        else:
            # Send error message
            self.iface.messageBar().pushMessage('Error', 
                                           'Failed to find time series.',
                                           level=QgsMessageBar.CRITICAL,
                                           duration=3)
    
    def config_closed(self):
        """ Close and disconnect the configuration dialog """
        self.config.accepted.disconnect()
        self.config.canceled.disconnect()
        self.config.close()

    def init_controls(self):
        """ Initialize and add signals to the left side control widget """
        print 'DEBUG %s : init_controls'
        # Create widget
        self.ctrl = ControlPanel(self.iface)
        # Create dock & add control widget
        self.ctrl_dock = QDockWidget('TS Tools Controls',
                                     self.iface.mainWindow())
        self.ctrl_dock.setObjectName('TS Tools Controls')
        self.ctrl_dock.setWidget(self.ctrl)
        # Add to iface
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.ctrl_dock)

    def init_plots(self):
        """ Initialize and add signals to plots within bottom dock """
        # Create time series plot
        self.ts_plot = TSPlot(self.iface)
        # TODO more plots, tabs
        
        # Create dock and add
        self.plot_dock = QDockWidget('Plots', self.iface.mainWindow())
        self.plot_dock.setObjectName('Plots') 
        self.plot_dock.setWidget(self.ts_plot)
        
        # Add to iface
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.plot_dock)

    def initGui(self):
        """ Required method for Qt to load components. 

        Load controls, plot, and init the signal controller
        """
        self.init_controls()
        self.init_plots()
        # TODO plots
        self.controller = Controller(self.iface, self.ctrl, self.ts_plot)

    def plot_request(self, pos, button=None):
        """ Request handler for QgsMapToolEmitPoint. Gets position and sends
        signal to controller to grab data & plot 
        """
        # Check if user has a layer added
        if self.canvas.layerCount() == 0 or pos is None:
            self.iface.messageBar().pushMessage('Error',
                'Please add a layer before clicking...',
                level=QgsMessageBar.WARNING,
                duration=3)

        # Check currently selected layer #TODO remove?
        layer = self.canvas.currentLayer()
        if (layer is None or
                not layer.isValid() or
                layer.type() != QgsMapLayer.RasterLayer):
            self.iface.messageBar().pushMessage('Info',
                'Please select a layer from time series before clicking',
                level=QgsMessageBar.WARNING,
                duration=2)
            return

        # Check if position needs to be reprojected to layer CRS
        layer_crs = layer.crs()
        map_crs = self.canvas.mapRenderer().destinationCrs()

        if not map_crs == layer_crs:
            if self.canvas.hasCrsTransformEnabled():
                crs_transform = QgsCoordinateTransform(map_crs, layer_crs)
                try:
                    pos = crs_transform.transform(pos)
                except:
                    self.iface.messageBar().pushMessage('Error',
                        'Could not convert map CRS to layer CRS',
                        level=QgsMessageBar.ERROR,
                        duration = 5)
                    return
            else:
                self.iface.messageBar().pushMessage('Error',
                    'Could not convert map CRS to layer CRS',
                    level=QgsMessageBar.ERROR,
                    duration = 5)
                return
        
        # Fetch data if inside raster
        if layer and layer.extent().contains(pos):        
            # Display message
            self.iface.messageBar().pushMessage('Info', 
                'Fetching time series',
                level=QgsMessageBar.INFO,
                duration=5)           
            
            # Fetch data and update
            self.controller.fetch_data(pos)
            self.controller.update_display()

            if setting.canvas['show_click']:
                self.controller.show_click(pos)

            # Clear message
            self.iface.messageBar().clearWidgets()

        else:
            self.iface.messageBar().pushMessage('Warning',
                'Please select a point within the time series image',
                level=QgsMessageBar.WARNING,
                duration = 5)


    def unload(self):
        """ Shutdown and disconnect """
        # Remove toolbar icons
        self.iface.removeToolBarIcon(self.action)
        self.iface.removeToolBarIcon(self.action_cfg)
        # Disconnect signals
        self.controller.disconnect()


