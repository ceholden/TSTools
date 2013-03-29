# -*- coding: utf-8 -*-
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

# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the widget
from ccdcwidget import CCDCWidget

class CCDCTools:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

    def initGui(self):
        # Create widget
        self.plotWidget = CCDCWidget(self.iface)
        # Create DockWidget and add CCDCWidget
        self.dockWidget = QDockWidget("CCDC Tools", self.iface.mainWindow())
        self.dockWidget.setObjectName("CCDC Tools")
        self.dockWidget.setWidget(self.plotWidget)
        # Connect signal for showing/hiding widget
        QObject.connect(self.dockWidget,
			SIGNAL('visibilityChanged ( bool )'),
			self.showHideDockWidget)
            
        # Add dockWidget to iface
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockWidget)

    def unload(self):
        # Close dock & disconnect widget
        self.dockWidget.close()
        self.plotWidget.disconnect()
        # Remove dock from interface
        self.iface.removeDockWidget(self.dockWidget)

    def showHideDockWidget(self):
        # Enable the widget if visibile & active
        if (self.dockWidget.isVisible() and 
			self.plotWidget.cbox_active.isChecked()):
            state = Qt.Checked
        else:
        	state = Qt.Unchecked
		self.plotWidget.set_active(state)
