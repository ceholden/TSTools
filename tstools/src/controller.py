""" Controller for TSTools that handles slots/signals communication
"""
import copy
from datetime import datetime as dt
from functools import partial
import itertools
import logging

import matplotlib as mpl
import numpy as np
try:
    import palettable
    HAS_PALETTABLE = True
except:
    HAS_PALETTABLE = False

from PyQt4 import QtCore, QtGui

import qgis

from . import config
from . import plots
from . import settings
from .utils import actions
from .logger import qgis_log
from .ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')

# PyQt -- moveToThread and functools.partial -- why doesn't it work?
# See:
# http://stackoverflow.com/questions/23317195/pyqt-movetothread-does-not-work-when-using-partial-for-slot


class Worker(QtCore.QObject):

    update = QtCore.pyqtSignal(float)
    finished = QtCore.pyqtSignal()
    errored = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super(Worker, self).__init__()
        parent.fetch_data.connect(self.fetch)

    @QtCore.pyqtSlot(object, object, str)
    def fetch(self, ts, pos, crs_wkt):
        logger.info('Fetching from QThread (id: %s)' %
                    hex(self.thread().currentThreadId()))
        # Fetch data
        try:
            for percent in ts.fetch_data(pos[0], pos[1], crs_wkt):
                self.update.emit(percent)
        except Exception as e:
            self.errored.emit(e.message)
        else:
            self.finished.emit()


class PlotHandler(QtCore.QObject):
    """ Workaround for connecting `pick_event` signals to `twinx()` axes

    Forwards `pick_event` signal to an axis onward.

    Args:
      canvas (matplotlib.backend_bases.FigureCanvasBase): figure canvas to
        connect
      tolerance (float or int): tolerance for picking plot point in days
        (default: 10)

    """
    picked = QtCore.pyqtSignal(set)

    def __init__(self, canvas, tolerance=2):
        super(PlotHandler, self).__init__()
        self.canvas = canvas
        self.tolerance = tolerance
        self.cid = self.canvas.mpl_connect('button_release_event', self)

    def __call__(self, event):
        # Plot X/Y clicked
        x, y = event.x, event.y
        # Bands plotted on each axis
        plotted = (settings.plot['y_axis_1_band'],
                   settings.plot['y_axis_2_band'])

        # Store output as a set
        images = set()
        for ax, _plotted in zip(event.canvas.axes, plotted):
            # If nothing plotted on this axis, continue
            if not np.any(_plotted):
                continue

            # Setup transform for going from data to plot coordinates
            trans = ax.transData

            # Check bands that are plotted on current axis
            on = np.where(_plotted)[0]
            on_series = settings.plot_series[on]
            on_band = settings.plot_band_indices[on]

            for i, j in zip(on_series, on_band):
                # Switch based on plot type
                if isinstance(event.canvas, plots.TSPlot):
                    _X, _y = tsm.ts.get_data(i, j, mask=False)
                    _x = _X['ordinal']
                elif isinstance(event.canvas, plots.ResidualPlot):
                    residuals = tsm.ts.get_residuals(i, j)
                    if residuals is None:
                        return
                    _x = np.array([dt.toordinal(_d) for _d in
                                   np.concatenate(residuals[0])])
                    _y = np.concatenate(residuals[1])
                elif isinstance(event.canvas, plots.DOYPlot):
                    _X, _y = tsm.ts.get_data(i, j, mask=False)
                    _x = _X['doy']

                # Transform data into plot coordinates
                trans_coords = trans.transform(np.vstack((_x, _y)).T)
                _x, _y = trans_coords[:, 0], trans_coords[:, 1]

                delta_x = np.abs(_x - x)
                delta_y = np.abs(_y - y)

                delta = np.linalg.norm(np.vstack((delta_x, delta_y)), axis=0)

                clicked = np.where(delta < self.tolerance)[0]

                for _clicked in clicked:
                    # Add index of series and index of image
                    images.add((i, _clicked))

        self.picked.emit(images)

    def disconnect(self):
        self.canvas.mpl_disconnect(self.cid)


class Controller(QtCore.QObject):
    """ Controller class for handling signals/slots

    Attributes:
      controls (ControlPanel): control panel instance
      plots (list): list of Plot* instances

    """
    controls = None
    plots = []
    working = False
    worker = None
    work_thread = None

    fetch_data = QtCore.pyqtSignal(object, object, str)

    initialized = False

    def __init__(self, controls, plots, parent=None):
        super(Controller, self).__init__()
        self.controls = controls
        self.plots = plots
        self.plot_events = []  # Matplotlib event handlers

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
            self.disconnect()
            self.config_closed()
            self._ts_init()
            self.initialized = True

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
        self._init_plot_symbology()
        self._init_raster_symbology()

        # Setup controls
        self.controls.init_ts()
        self.controls.plot_options_changed.connect(self.update_plot)
        self.controls.plot_save_requested.connect(self.save_plot)
        self.controls.image_table_row_clicked.connect(self._add_remove_image)
        self.controls.symbology_applied.connect(
            lambda: actions.apply_symbology())

        # Setup plots
        self._init_plots()
        self.update_plot()

# PLOT TOOL
    @QtCore.pyqtSlot(object)
    def plot_request(self, pos):
        if self.working:
            qgis_log('Unable to initiate plot request: already working',
                     logging.INFO)
        else:
            qgis_log('Clicked a point: {p} ({t})'.format(p=pos, t=type(pos)),
                     level=logging.INFO)

            crs = qgis.utils.iface.mapCanvas().mapRenderer().destinationCrs()
            crs_wkt = crs.toWkt()

            # Setup QProgressBar
            self.progress_bar = qgis.utils.iface.messageBar().createMessage(
                'Retrieving data')

            self.progress = QtGui.QProgressBar()
            self.progress.setValue(0)
            self.progress.setMaximum(100)
            self.progress.setAlignment(QtCore.Qt.AlignLeft |
                                       QtCore.Qt.AlignVCenter)

            self.but_cancel = QtGui.QPushButton('Cancel')
            self.but_cancel.pressed.connect(self.plot_request_cancel)

            self.progress_bar.layout().addWidget(self.progress)
            self.progress_bar.layout().addWidget(self.but_cancel)

            qgis.utils.iface.messageBar().pushWidget(
                self.progress_bar, qgis.utils.iface.messageBar().INFO)

            # Setup worker and thread
            self.working = True

            self.work_thread = QtCore.QThread()
            # self.worker = Worker()
            self.worker = Worker(self)
            self.worker.moveToThread(self.work_thread)
            self.worker.update.connect(self.plot_request_update)
            self.worker.finished.connect(self.plot_request_finish)
            self.worker.errored.connect(self.plot_request_error)
            self.work_thread.started.connect(partial(self.plot_request_start,
                                             tsm.ts,
                                             (pos[0], pos[1]),
                                             crs_wkt))

            if (getattr(self.controls, 'custom_form', None) is not None and
                    hasattr(tsm.ts, 'set_custom_controls')):
                try:
                    options = self.controls.custom_form.get()
                    tsm.ts.set_custom_controls(options)
                except Exception as e:
                    logger.warning(
                        'Could not use custom controls for timeseries')
                    qgis_log(e.message, level=logging.WARNING)
                    self.controls.custom_form.reset()
                    return

            # Run thread
            logger.info('Timeseries (id: {i})'.format(i=hex(id(tsm.ts))))
            logger.info('Current thread: ({i})'.format(
                i=hex(self.thread().currentThreadId())))

            self.work_thread.start()
            logger.info('Started QThread (id: {i})'.format(
                i=hex(self.work_thread.currentThreadId())))

    @QtCore.pyqtSlot(object, tuple, str)
    def plot_request_start(self, ts, pos, crs_wkt):
        logger.info('Fetch data signal sent for point: '
                    '{p} ({t})'.format(p=pos, t=type(pos)))

        self.fetch_data.emit(ts, pos, crs_wkt)

    @QtCore.pyqtSlot(float)
    def plot_request_update(self, progress):
        if self.working is True:
            self.progress.setValue(progress)

    @QtCore.pyqtSlot()
    def plot_request_finish(self):
        # Get results in this thread since it's so prone to error
        try:
            tsm.ts.fetch_results()
        except Exception as e:
            logger.error('Could not fetch results: %s' % e.message)
            raise
        finally:
            # Stop 'working'
            self.working = False
            self.work_thread.quit()

            # Clear GUI messages
            logger.info('Plot request finished')
            qgis.utils.iface.messageBar().clearWidgets()

            # Update controls
            self.controls.plot_option_changed(emit=False)

            # Update plots
            self.update_plot()

            # Add geometry from clicked point
            self.plot_request_geometry()

    @QtCore.pyqtSlot(str)
    def plot_request_error(self, txt):
        qgis.utils.iface.messageBar().clearWidgets()
        qgis_log(txt, logging.ERROR, duration=5)

        self.working = False
        self.work_thread.quit()

    @QtCore.pyqtSlot()
    def plot_request_cancel(self):
        self.plot_request_finish()

    def plot_request_geometry(self):
        """ Add polygon of geometry from clicked X/Y coordinate """
        # Record currently selected feature so we can restore it
        last_selected = qgis.utils.iface.activeLayer()

        geom_wkt, proj_wkt = tsm.ts.get_geometry()
        geom_qgis = qgis.core.QgsGeometry.fromWkt(geom_wkt)
        proj_qgis = qgis.core.QgsCoordinateReferenceSystem()
        proj_qgis.createFromWkt(proj_wkt)

        # Update existing layer
        if settings.canvas['click_layer_id'] is not None:
            # Update to new row/column
            vlayer = qgis.core.QgsMapLayerRegistry.instance().mapLayers()[
                settings.canvas['click_layer_id']]
            vlayer.startEditing()
            pr = vlayer.dataProvider()
            # attrs = pr.attributeIndexes()
            for feat in vlayer.getFeatures():
                vlayer.changeAttributeValue(feat.id(), 0, tsm.ts.pixel_pos)
                vlayer.changeGeometry(feat.id(), geom_qgis)
                vlayer.setCrs(proj_qgis)
            vlayer.commitChanges()
            vlayer.updateExtents()
            vlayer.triggerRepaint()
        # Create new layer
        else:
            uri = 'polygon?crs=%s' % proj_wkt
            vlayer = qgis.core.QgsVectorLayer(uri, 'Query', 'memory')
            pr = vlayer.dataProvider()
            vlayer.startEditing()
            pr.addAttributes([
                qgis.core.QgsField('position', QtCore.QVariant.String)
            ])
            feat = qgis.core.QgsFeature()
            feat.setGeometry(geom_qgis)
            feat.setAttributes([tsm.ts.pixel_pos])
            pr.addFeatures([feat])

            # See: http://lists.osgeo.org/pipermail/qgis-developer/2011-April/013772.html
            props = {
                'color_border': '255, 0, 0, 255',
                'style': 'no',
                'style_border': 'solid',
                'width': '0.40'
            }
            s = qgis.core.QgsFillSymbolV2.createSimple(props)
            vlayer.setRendererV2(qgis.core.QgsSingleSymbolRendererV2(s))
            vlayer.commitChanges()
            vlayer.updateExtents()

            vlayer_id = qgis.core.QgsMapLayerRegistry.instance().addMapLayer(
                vlayer).id()
            if vlayer_id:
                settings.canvas['click_layer_id'] = vlayer_id
            else:
                logger.warning('Could not get ID of "query" layer')

        # Restore active layer
        qgis.utils.iface.setActiveLayer(last_selected)

# LAYER MANIPULATION
    @QtCore.pyqtSlot(set)
    def _plot_add_layer(self, idx):
        """ Add or remove image described by idx

        Args:
          idx (list): list of tuples (index of series, index of image) to add
            or remove

        """
        for i_series, i_img in idx:
            self._add_remove_image(i_series, i_img)

    @QtCore.pyqtSlot(list)
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

    @QtCore.pyqtSlot(list)
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

    @QtCore.pyqtSlot(int, int)
    def _add_remove_image(self, i_series, i_image):
        """ Add or remove image at index `i_image`
        """
        layers = qgis.core.QgsMapLayerRegistry.instance().mapLayers().values()
        filename = tsm.ts.series[i_series].images['path'][i_image]

        # Add image
        if filename not in [layer.source() for layer in layers]:
            rlayer = qgis.core.QgsRasterLayer(
                tsm.ts.series[i_series].images['path'][i_image],
                tsm.ts.series[i_series].images['id'][i_image])

            if rlayer.isValid():
                qgis.core.QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                settings.image_layers.append(rlayer)
                actions.apply_symbology(rlayer)
        # Remove image
        else:
            layer_id = [l.id() for l in layers if l.source() == filename][0]
            qgis.core.QgsMapLayerRegistry.instance().removeMapLayer(layer_id)

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

# PLOT SYMBOLOGY / SETTINGS
    def _init_plot_symbology(self):
        logger.debug('Initialize plot symbology')
        # Setup colors to cycle
        if HAS_PALETTABLE:
            if hasattr(palettable, 'wesanderson'):
                # Zissou and Darjeeling combined for 9 colors
                colors = (palettable.wesanderson.get_map('Zissou').colors +
                          palettable.wesanderson.get_map('Darjeeling1').colors)
            else:
                colors = palettable.colorbrewer.get_map(
                    'Set1', 'Qualitative', 9).colors
        else:
            colors = mpl.cm.Set1(np.linspace(0, 1, 9), bytes=True)[:, :-1]

        # Initialize plot symbology for each series in timeseries
        settings.plot_symbol = []
        color_cycle = itertools.cycle(colors)
        for s, b in zip(settings.plot_series, settings.plot_band_indices):
            symbol = copy.deepcopy(settings.default_plot_symbol)

            n_image = tsm.ts.series[s].images.shape[0]
            symbol.update({
                'indices': [np.arange(n_image)],
                'markers': ['o'],
                'colors': [color_cycle.next()]
            })

            settings.plot_symbol.append(symbol)

# CONTROLS
    def _init_plot_options(self):
        """ Initialize plot control data
        """
        logger.debug('Initialize plot options')
        settings.plot_series = []
        settings.plot_band_indices = []
        settings.plot_bands = []
        for i, series in enumerate(tsm.ts.series):
            settings.plot_series.extend([i] * len(series.band_names))
            settings.plot_band_indices.extend(range(len(series.band_names)))
            settings.plot_bands.extend(['%s - %s' %
                                        (series.description, name) for
                                        name in series.band_names])
        settings.plot_series = np.asarray(settings.plot_series)
        settings.plot_band_indices = np.asarray(settings.plot_band_indices)
        settings.plot_bands = np.asarray(settings.plot_bands)

        n_bands = len(settings.plot_bands)

        # No bands plotted on axes initially
        settings.plot['y_axis_1_band'] = np.zeros(n_bands, dtype=np.bool)
        settings.plot['y_axis_2_band'] = np.zeros(n_bands, dtype=np.bool)

        # Default min/max on plot
        settings.plot['y_min'] = [0, 0]  # TODO:HARDCODE
        settings.plot['y_max'] = [10000, 10000]  # TODO:HARDCODE
        settings.plot['x_min'] = min([series.images['date'].min()
                                      for series in tsm.ts.series]).year
        settings.plot['x_max'] = max([series.images['date'].max()
                                      for series in tsm.ts.series]).year

        # Default mask values and fit/break on/off
        settings.plot['mask_val'] = tsm.ts.mask_values.copy()
        settings.plot['fit'] = True if tsm.ts.has_results else False
        settings.plot['break'] = True if tsm.ts.has_results else False

    def _init_raster_symbology(self):
        """ Initialize image symbology
        """
        logger.debug('Initialize raster symbology')
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
                i = [min(n_bands - 1, _i) for _i in
                     series.symbology_hint_indices]
                if isinstance(i, (tuple, list)):
                    if len(i) == 3:
                        logger.debug('Applying RGB symbology hint')
                        symbol.update({
                            'type': 'RGB',
                            'band_red': i[0],
                            'band_green': i[1],
                            'band_blue': i[2]
                        })
                    elif len(i) == 1:
                        logger.debug('Applying GREY symbology hint')
                        symbol.update({
                            'type': 'GREY',
                            'band_red': i[0],
                            'band_green': i[0],
                            'band_blue': i[0]
                        })
                else:
                    logger.warning(
                        'Symbology RGB band hint improperly described')

            if hasattr(series, 'symbology_hint_minmax'):
                i = series.symbology_hint_minmax
                if isinstance(i, (tuple, list)):
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
                    elif (isinstance(i[0], (list, np.ndarray)) and
                            isinstance(i[1], (list, np.ndarray)) and
                            len(i[0]) == n_bands and len(i[1]) == n_bands):
                        logger.debug(
                            'Applying specified min/max symbology hint')
                        symbol.update({
                            'min': np.asarray(i[0]),
                            'max': np.asarray(i[1])
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
        """ Initialize plot data """
        # Disconnect any existing signals
        for pe in self.plot_events:
            pe.disconnect()
            pe.deleteLater()
            pe = None

        for plt in self.plots:
            plt.reset()

        # Connect plot signals for adding images
        self.plot_events = []
        for plot in self.plots:
            handler = PlotHandler(plot.fig.canvas,
                                  tolerance=settings.plot['picker_tol'])
            handler.picked.connect(self._plot_add_layer)
            self.plot_events.append(handler)

    def update_plot(self):
        # Update mask if needed
        if not np.array_equal(tsm.ts.mask_values, settings.plot['mask_val']):
            tsm.ts.update_mask(settings.plot['mask_val'])
            # Re-calculate scale
            # TODO: already do this in controls but not before we update mask
            if settings.plot['y_axis_scale_auto'][0]:
                actions.calculate_scale(0)
            if settings.plot['y_axis_scale_auto'][1]:
                actions.calculate_scale(1)

        # Update plots -- only visible
        for i, plot in enumerate(self.plots):
            if i == settings.plot_current:
                settings.plot_dirty[i] = False
                plot.plot()
            else:
                settings.plot_dirty[i] = True

    def save_plot(self):
        qgis_log('Saving plot', logging.DEBUG)

# DISCONNECT
    def disconnect(self):
        logger.info('Disconnecting controller')
        if not self.initialized:
            return

        # Swallow error:
        #   layer registry can be deleted before this runs when closing QGIS
        try:
            qgis.core.QgsMapLayerRegistry.instance()\
                .layersAdded.disconnect(self._map_layers_added)
            qgis.core.QgsMapLayerRegistry.instance()\
                .layersWillBeRemoved.disconnect(self._map_layers_removed)
        except:
            pass

        # Disconnect plot mouse event signals
        for pe in self.plot_events:
            pe.disconnect()
            pe.deleteLater()
            pe = None

        # Controls
        self.controls.disconnect()
        self.controls.plot_options_changed.disconnect(self.update_plot)
        self.controls.plot_save_requested.disconnect(self.save_plot)
        self.controls.image_table_row_clicked.disconnect(
            self._add_remove_image)
        self.controls.symbology_applied.disconnect()

        self.initialzed = False
