""" Controller for TSTools that handles slots/signals communication
"""
import copy
from functools import partial
import logging

import numpy as np

from PyQt4 import QtCore

import qgis

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
            raise  # TODO: REMOVE EXCEPTION
        else:
            qgis_log('Loaded timeseries: {d}'.format(d=tsm.ts.description))
            self.config_closed()
            self._ts_init()

    def _ts_init(self):
        """ Initialize control and plot views with data from timeseries driver
        """
        # Connect QgsMapLayerRegistry signals
        qgis.core.QgsMapLayerRegistry.instance().layersAdded.connect(
            self._map_layers_added)
        qgis.core.QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(
            self._map_layers_removed)

        # Prepare TS driver data for controls
        self._init_plot_options()
        self._init_symbology()

        # Setup controls
        self.controls.init_ts()
        self.controls.image_table_row_clicked.connect(
            partial(self._add_remove_image, settings.series_index_table))

# LAYER MANIPULATION
    @QtCore.pyqtSlot()
    def _map_layers_added(self, layers):
        """ Performs necessary functions if added layers in timeseries

        Check if all newly added layers are part of timeseries. If so, then:
            - Set timeseries image checkbox in images table to checked state

        Args:
          layers (QList<QgsMapLayer *>): list of QgsMapLayers

        """
        for layer in layers:
            for i, series in enumerate(tsm.ts.series):
                rows_added = [row for row, path in
                              enumerate(series.images['path'])
                              if layer.source() == path]
                for row in rows_added:
                    logger.debug('Added image: {img}'.format(
                        img=series.images['id'][row]))
                    item = self.controls.image_tables[i].item(row, 0)
                    if item:
                        if item.checkState() == QtCore.Qt.Unchecked:
                            item.setCheckState(QtCore.Qt.Checked)

    @QtCore.pyqtSlot()
    def _map_layers_removed(self, layer_ids):
        """ Perform necessary functions if removed layers in timeseries

        Args:
          layer_ids (QStringList theLayerIds): list of layer IDs

        """
        for layer_id in layer_ids:
            # Get QgsMapLayer instance for ID
            layer = qgis.core.QgsMapLayerRegistry.instance().mapLayers()[
                layer_id]

            # Remove from settings
            if layer in settings.image_layers:
                settings.image_layers.remove(layer)

            # Remove from table
            for i, series in enumerate(tsm.ts.series):
                rows_removed = [
                    row for row, (_id, path) in
                    enumerate(zip(series.images['id'], series.images['path']))
                    if _id in layer_id or path in layer_id
                ]

                for row in rows_removed:
                    item = self.controls.image_tables[i].item(row, 0)
                    if item and item.checkState() == QtCore.Qt.Checked:
                        item.setCheckState(QtCore.Qt.Unchecked)

            # Check for click layer
            if settings.canvas['click_layer_id'] == layer_id:
                logger.debug('Removed Query layer')
                settings.canvas['click_layer_id'] = None

    @QtCore.pyqtSlot(int)
    def _add_remove_image(self, i_table, i_image):
        """ Add or remove image at index `i_image`
        """
        layers = qgis.core.QgsMapLayerRegistry.instance().mapLayers().values()
        filename = tsm.ts.series[i_table].images['path'][i_image]

        # Add image
        if filename not in [layer.source() for layer in layers]:
            rlayer = qgis.core.QgsRasterLayer(
                tsm.ts.series[i_table].images['path'][i_image],
                tsm.ts.series[i_table].images['id'][i_image])

            if rlayer.isValid():
                qgis.core.QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                settings.image_layers.append(rlayer)
                self._apply_symbology(rlayer)
        # Remove image
        else:
            layer_id = [l.id() for l in layers if l.source() == filename][0]
            qgis.core.QgsMapLayerRegistry.instance().removeMapLayer(layer_id)

    def _apply_symbology(self, rlayer):
        """ Apply symbology to a raster layer
        """
        logger.debug('Applying symbology to raster layer: {r} ({m})'.format(
            r=rlayer.id(), m=hex(id(rlayer))))


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
    def _init_plot_options(self):
        """ Initialize plot control data
        """
        settings.plot_bands = []
        settings.plot_series = []
        for i, series in enumerate(tsm.ts.series):
            settings.plot_bands.extend(series.band_names)
            settings.plot_series.extend([i] * len(series.band_names))

        n_bands = len(settings.plot_bands)

        # No bands plotted on axes initially
        settings.plot['y_axis_1_band'] = np.zeros(n_bands, dtype=np.bool)
        settings.plot['y_axis_2_band'] = np.zeros(n_bands, dtype=np.bool)

        # Default min/max on plot
        settings.plot['y_min'] = [0, 0]  # TODO:HARDCODE
        settings.plot['y_max'] = [10000, 10000]  # TODO:HARDCODE
        settings.plot['x_min'] = min([series.images['date'].min()
                                      for series in tsm.ts.series]).year
        settings.plot['x_max'] = max([series.images['date'].min()
                                      for series in tsm.ts.series]).year

    def _init_symbology(self):
        """ Initialize image symbology
        """
        settings.symbol = []
        for i, series in enumerate(tsm.ts.series):
            # Setup symbology settings for series
            symbol = copy.deepcopy(settings.default_symbol)

            n_bands = len(series.band_names)
            # Default min/max
            symbol['min'] = np.zeros(n_bands, dtype=np.int32)
            symbol['max'] = np.ones(n_bands, dtype=np.int32) * 10000

            # Custom symbology, if exists
            if hasattr(series, 'symbology_hint_indices'):
                i = series.symbology_hint_indices
                if isinstance(i, (tuple, list)) and len(i) == 3:
                    logger.debug('Applying RGB symbology hint')
                    symbol.update({
                        'band_red': i[0],
                        'band_green': i[1],
                        'band_blue': i[2]
                    })
                else:
                    logger.warning(
                        'Symbology RGB band hint improperly described')

            if hasattr(series, 'symbology_hint_minmax'):
                i = series.symbology_hint_minmax
                if isinstance(i, (tuple, list)) and len(i) == 2:
                    # One min/max or a set of them
                    if isinstance(i[1], (int, float)) and \
                            isinstance(i[0], (int, float)):
                        logger.debug(
                            'Applying min/max symbology hint for all bands')
                        symbol.update({
                            'min': np.ones(n_bands, dtype=np.int32) * i[0],
                            'max': np.ones(n_bands, dtype=np.int32) * i[1],
                        })
                    # Min/max for each band
                    elif isinstance(i[0], np.ndarray) and \
                            isinstance(i[1], np.ndarray):
                        logger.debug(
                            'Applying specified min/max symbology hint')
                        settings.symbol.update({
                            'min': i[0],
                            'max': i[1]
                        })
                    else:
                        logger.warning(
                            'Could not parse symbology min/max hint')
                else:
                    logger.warning(
                        'Symbology min/max hint improperly described')

            # Add to settings
            settings.symbol.append(symbol)

# PLOTS
    def _init_plots(self):
        pass

# DISCONNECT
    def disconnect(self):
        qgis.core.QgsMapLayerRegistry.instance()\
            .layersAdded.disconnect()
        qgis.core.QgsMapLayerRegistry.instance()\
            .layersWillBeRemoved.disconnect()

        # Controls
        self.controls.plot_options_changed.disconnect()
        self.controls.plot_save_requested.disconnect()
        self.controls.image_table_row_clicked.disconnect()
