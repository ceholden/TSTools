""" Point of entry to plugin.

Adds plugin tools to toolbar and initializes controller, UI controls, plots,
and timeseries manager.
"""
import functools
import logging
import os

from PyQt4 import QtCore
from PyQt4 import QtGui

import qgis.gui

# Initialize Qt resources from file resources.py -- ignore unused warning
import resources_rc

from .ts_driver.ts_manager import tsm
from . import controller
from .controls import controls
from . import plots
from . import settings
from .logger import qgis_log

logger = logging.getLogger('tstools')


class TSTools(QtCore.QObject):

    controls = None
    plots = []

    def __init__(self, iface):
        super(TSTools, self).__init__()
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.previous_tool = None

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QtCore.QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir,
                                  'i18n',
                                  'tstools_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QtCore.QTranslator()
            self.translator.load(localePath)

            if QtCore.qVersion() > '4.3.3':
                QtCore.QCoreApplication.installTranslator(self.translator)

        # Initialize rest of GUI
        self.init_controls()
        self.init_plots()

        # Init controller
        self.controller = controller.Controller(self.controls, self.plots)

# SLOTS
    @QtCore.pyqtSlot()
    def set_tool(self):
        """ Sets the time series tool as current map tool
        """
        settings.tool_enabled = True
        self.previous_tool = self.canvas.mapTool()
        self.canvas.setMapTool(self.tool_ts)

# GUI
    def init_controls(self):
        """ Initialize controls for plugin """
        self.controls = controls.ControlPanel(self.iface)

        self.control_dock = QtGui.QDockWidget('TSTools Controls',
                                              self.iface.mainWindow())
        self.control_dock.setObjectName('TSTools Controls')
        self.control_dock.setWidget(self.controls)

        self.iface.addDockWidget(QtCore.Qt.LeftDockWidgetArea,
                                 self.control_dock)

    def init_plots(self):
        """ Initialize plots used in plugin """
        self.plot_dock = QtGui.QDockWidget('TSTools Plots',
                                           self.iface.mainWindow())
        self.plot_dock.setObjectName('TSTools Plots')

        for plot in plots.plots:
            self.plots.append(plot(self.iface))

        self.plot_tabs = QtGui.QTabWidget(self.plot_dock)
        for plot in self.plots:
            self.plot_tabs.addTab(plot, plot.__str__())

        self.plot_dock.setWidget(self.plot_tabs)
        self.iface.addDockWidget(QtCore.Qt.BottomDockWidgetArea,
                                 self.plot_dock)

    def initGui(self):
        """ Load toolbar for plugin """
        # MapTool button
        self.action = QtGui.QAction(
            QtGui.QIcon(':/plugins/tstools/media/tstools_click.png'),
            'Time Series Tools',
            self.iface.mainWindow())
        self.action.triggered.connect(self.set_tool)
        self.iface.addToolBarIcon(self.action)

        # Configuration menu button
        self.action_cfg = QtGui.QAction(
            QtGui.QIcon(':/plugins/tstools/media/tstools_config.png'),
            'Configure',
            self.iface.mainWindow())
        self.action_cfg.triggered.connect(
            functools.partial(self.controller.open_config, self))
        self.iface.addToolBarIcon(self.action_cfg)

        # Map tool
        self.tool_ts = qgis.gui.QgsMapToolEmitPoint(self.canvas)
        self.tool_ts.setAction(self.action)
        self.tool_ts.canvasClicked.connect(self.controller.plot_request)

    def unload(self):
        """ Shutdown and disconnect """
        # Remove toolbar icons
        self.iface.removeToolBarIcon(self.action)
        self.iface.removeToolBarIcon(self.action_cfg)
        self.canvas.setMapTool(self.previous_tool)
