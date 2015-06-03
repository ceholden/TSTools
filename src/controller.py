""" Controller for TSTools that handles slots/signals communication
"""
import logging

import numpy as np

from PyQt4 import QtCore

from . import config
from . import settings
from .logger import qgis_log
from .ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


class Controller(object):
    """ Controller class for handling signals/slots

    Attributes:
      controls (ControlPanel): control panel instance
      plots (list): list of Plot* instances

    """
    controls = None
    plots = []

    def __init__(self, controls, plots):
        self.controls = controls
        self.plots = plots

# TIMESERIES
    def get_timeseries(self, driver, location, custom_config=None):
        """ Initialize timeseries selected by user
        """
        try:
            tsm.ts = driver(location, config=custom_config)
        except Exception as e:
            msg = 'Failed to open timeseries: {msg}'.format(msg=e.message)
            qgis_log(msg, level=logging.ERROR, duration=5)
        else:
            qgis_log('Loaded timeseries: {d}'.format(d=tsm.ts.description))
            self.config_closed()
            self._ts_init()

# CONFIG
    @QtCore.pyqtSlot()
    def open_config(self, parent=None):
        self.config = config.Config()
        self.config.accepted.connect(self.config_accepted)
        self.config.canceled.connect(self.config_closed)
        self.config.exec_()

    @QtCore.pyqtSlot()
    def config_accepted(self):
        # Temporary values
        location = str(self.config.location)
        ts_index = int(self.config.model_index)
        custom_config = self.config.custom_options

        driver = tsm.ts_drivers[ts_index]

        logger.info('ACCEPTED CONFIG')
        logger.info(location)
        logger.info(ts_index)
        logger.info(custom_config)

        self.get_timeseries(driver, location, custom_config)

    @QtCore.pyqtSlot()
    def config_closed(self):
        self.config.accepted.disconnect()
        self.config.canceled.disconnect()
        self.config.close()

        self.config = None

# CONTROLS
    def _ts_init(self):
        """ Initialize control and plot views with data from timeseries driver
        """
        # Prepare TS driver data for controls
        self._init_plot_options()
        self._init_symbology()

        # Setup controls
        self.controls.init_ts()

    def _init_plot_options(self):
        """ Initialize plot control data
        """
        n_bands = len(tsm.ts.band_names)

        # No bands plotted on axes initially
        settings.plot['y_axis_1_band'] = np.zeros(n_bands, dtype=np.bool)
        settings.plot['y_axis_2_band'] = np.zeros(n_bands, dtype=np.bool)

        # Default min/max on plot
        settings.plot['y_min'] = [0, 0]  # TODO:HARDCODE
        settings.plot['y_max'] = [10000, 10000]  # TODO:HARDCODE
        settings.plot['x_min'] = min(tsm.ts.images['date']).year
        settings.plot['x_max'] = max(tsm.ts.images['date']).year

    def _init_symbology(self):
        """ Initialize image symbology
        """
        n_bands = len(tsm.ts.band_names)
        # Default min/max
        settings.symbol['y_min'] = np.zeros(n_bands, dtype=np.int32)
        settings.symbol['y_max'] = np.ones(n_bands, dtype=np.int32) * 10000

        # Custom symbology, if exists
        if hasattr(tsm.ts, 'symbology_hint_indices'):
            i = tsm.ts.symbology_hint_indices
            if isinstance(i, (tuple, list)) and len(i) == 3:
                logger.debug('Applying RGB symbology hint')
                settings.symbol.update({
                    'band_red': i[0],
                    'band_green': i[1],
                    'band_blue': i[2]
                })
            else:
                logger.warning('Symbology RGB band hint improperly described')

        if hasattr(tsm.ts, 'symbology_hint_minmax'):
            i = tsm.ts.symbology_hint_minmax
            if isinstance(i, (tuple, list)) and len(i) == 2:
                # One min/max or a set of them
                if isinstance(i[1], (int, float)) and \
                        isinstance(i[0], (int, float)):
                    logger.debug(
                        'Applying min/max symbology hint for all bands')
                    settings.symbol.update({
                        'min': np.ones(n_bands, dtype=np.int32) * i[0],
                        'max': np.ones(n_bands, dtype=np.int32) * i[1],
                    })
                # Min/max for each band
                elif isinstance(i[0], np.ndarray) and \
                        isinstance(i[1], np.ndarray):
                    logger.debug('Applying specified min/max symbology hint')
                    settings.symbol.update({
                        'min': i[0],
                        'max': i[1]
                    })
                else:
                    logger.warning('Could not parse symbology min/max hint')
            else:
                logger.warning('Symbology min/max hint improperly described')

# PLOTS
