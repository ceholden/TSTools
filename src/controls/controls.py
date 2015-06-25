# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 TSTools control widget
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
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
from collections import OrderedDict
from functools import partial
import logging

from PyQt4 import QtCore, QtGui

import numpy as np

from ..ui_controls import Ui_Controls

from .raster_symbology import RasterSymbologyControl
from .plot_symbology import SymbologyControl
from .plot_save import SavePlotDialog
from ..utils.custom_form import CustomForm

from .. import settings
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm
from ..utils import actions

logger = logging.getLogger('tstools')


def str2num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


class ControlPanel(QtGui.QWidget, Ui_Controls):

    plot_options_changed = QtCore.pyqtSignal()
    plot_save_requested = QtCore.pyqtSignal()
    image_table_row_clicked = QtCore.pyqtSignal(int)
    symbology_applied = QtCore.pyqtSignal()

    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QtGui.QWidget.__init__(self)
        self.setupUi(self)

    def init_ts(self):
        self._init_plot_options()
        self._init_table()
        self._init_symbology()
        self._init_custom_controls()

# PLOT TAB
    @QtCore.pyqtSlot(int)
    def _band_combox_pressed(self, index):
        # Do not run for "Select Plot Band" (first QComboBox item)
        if index.row() == 0:
            return

        item = self.combox_band.model().itemFromIndex(index)
        index = index.row() - 1
        name = settings.plot_bands[index]

        # Not on either axis -- move to axis 1
        if not settings.plot['y_axis_1_band'][index] and \
                not settings.plot['y_axis_2_band'][index]:
            settings.plot['y_axis_1_band'][index] = True
            item.setText(u'☒: ' + name)
        # On axis 1 -- move to axis 2
        elif settings.plot['y_axis_1_band'][index] and \
                not settings.plot['y_axis_2_band'][index]:
            settings.plot['y_axis_1_band'][index] = False
            settings.plot['y_axis_2_band'][index] = True
            item.setText(u'☑: ' + name)
        # On axis 2 -- turn off
        elif not settings.plot['y_axis_1_band'][index] and \
                settings.plot['y_axis_2_band'][index]:
            settings.plot['y_axis_1_band'][index] = False
            settings.plot['y_axis_2_band'][index] = False
            item.setText(u'☐: ' + name)

        # self.plot_options_changed.emit()
        # Update plot options
        self.plot_option_changed()

    @QtCore.pyqtSlot()
    def _plot_y_axis_changed(self):
        """ Switch Y-axis auto-scaling and min/max text """
        if self.rad_axis_1.isChecked():
            settings.plot['axis_select'] = 0
        elif self.rad_axis_2.isChecked():
            settings.plot['axis_select'] = 1

        axis = settings.plot['axis_select']

        self.cbox_yscale_auto.setChecked(
            settings.plot['y_axis_scale_auto'][axis])
        self.edit_ymin.setText(str(settings.plot['y_min'][axis]))
        self.edit_ymax.setText(str(settings.plot['y_max'][axis]))

        self.edit_ymin.setEnabled(not settings.plot['y_axis_scale_auto'][axis])
        self.edit_ymax.setEnabled(not settings.plot['y_axis_scale_auto'][axis])

    @QtCore.pyqtSlot(int)
    def _xrange_moved(self, minmax, value):
        """ Update X-axis min/max labels to slider values
        """
        if minmax == 'min':
            self.lab_xmin.setText(str(value))
        elif minmax == 'max':
            self.lab_xmax.setText(str(value))

    @QtCore.pyqtSlot(int)
    def _xrange_changed(self, minmax, value):
        """ Handle changes to X-axis range
        """
        if minmax == 'min':
            settings.plot['x_min'] = value
            self.lab_xmin.setText(str(value))
            if settings.plot['x_scale_fix']:
                # Adjust X-axis max if using fixed range
                settings.plot['x_max'] = value + settings.plot['x_scale_range']
                self.scroll_xmax.blockSignals(True)
                self.scroll_xmax.setValue(settings.plot['x_max'])
                self.lab_xmax.setText(str(settings.plot['x_max']))
                self.scroll_xmax.blockSignals(False)
            else:
                self.scroll_xmax.setMinimum(
                    value + self.scroll_xmax.singleStep())
        elif minmax == 'max':
            settings.plot['x_max'] = value
            self.lab_xmax.setText(str(value))
            if settings.plot['x_scale_fix']:
                # Adjust X-axis max if using fixed range
                settings.plot['x_min'] = value - settings.plot['x_scale_range']
                self.scroll_xmin.blockSignals(True)
                self.scroll_xmin.setValue(settings.plot['x_min'])
                self.lab_xmin.setText(str(settings.plot['x_min']))
                self.scroll_xmin.blockSignals(False)
            else:
                self.scroll_xmin.setMaximum(
                    value - self.scroll_xmin.singleStep())

        # Emit signal to trigger plot updates/etc
        self.plot_options_changed.emit()

    @QtCore.pyqtSlot(int)
    def _xrange_fixed(self, state):
        """ Turn on/off fixing date range for X-axis
        """
        if state == QtCore.Qt.Checked:
            settings.plot['x_scale_fix'] = True
            settings.plot['x_scale_range'] = (self.scroll_xmax.value() -
                                              self.scroll_xmin.value())
            # Set new min/max ranges
            self.scroll_xmin.setMaximum(self.scroll_xmax.maximum() -
                                        settings.plot['x_scale_range'])
            self.scroll_xmax.setMinimum(self.scroll_xmin.minimum() +
                                        settings.plot['x_scale_range'])
            # Display range
            self.cbox_xscale_fix.setText(
                'Fixed date range [range: {r}]'
                .format(r=settings.plot['x_scale_range']))
        elif state == QtCore.Qt.Unchecked:
            settings.plot['x_scale_fix'] = False
            settings.plot['x_scale_range'] = None
            # Restore original min/max ranges
            self.scroll_xmin.setMaximum(self.scroll_xmax.value() -
                                        self.scroll_xmax.singleStep())
            self.scroll_xmax.setMinimum(self.scroll_xmin.value() +
                                        self.scroll_xmin.singleStep())
            self.cbox_xscale_fix.setText('Fixed date range')

    @QtCore.pyqtSlot()
    def plot_option_changed(self, emit=True):
        """ Catch-all slot for plot control panel changes
        """
        logger.debug('Updating plot options')

        axis = settings.plot['axis_select']
        axis_2 = 1 if axis == 0 else 0

        # Update Y-axis values
        settings.plot['y_axis_scale_auto'][axis] = \
            self.cbox_yscale_auto.isChecked()
        if settings.plot['y_axis_scale_auto'][axis]:
            # Re-calculate scale
            actions.calculate_scale(axis)
            # Update texts
            self.edit_ymin.setText(str(settings.plot['y_min'][axis]))
            self.edit_ymax.setText(str(settings.plot['y_max'][axis]))
        if settings.plot['y_axis_scale_auto'][axis_2]:
            # Re-calculate scale, but don't update texts
            actions.calculate_scale(axis_2)

        settings.plot['y_min'][axis] = str2num(self.edit_ymin.text())
        settings.plot['y_max'][axis] = str2num(self.edit_ymax.text())

        # Enable/disable Y-axis min/max editing
        self.edit_ymin.setEnabled(not settings.plot['y_axis_scale_auto'][axis])
        self.edit_ymax.setEnabled(not settings.plot['y_axis_scale_auto'][axis])

        # Plot features
        settings.plot['mask'] = True if self.cbox_fmask.isChecked() else False
        settings.plot['fit'] = (True if self.cbox_modelfit.isChecked()
                                else False)
        settings.plot['break'] = (True if self.cbox_breakpoint.isChecked()
                                  else False)
        try:
            mask_vals = np.array([int(v) for v in self.edit_maskvalues.text()
                                  .replace(' ', ',').split(',') if v])
            settings.plot['mask_val'] = mask_vals
        except:
            qgis_log('Cannot parse mask values provided.')
            self.edit_maskvalues.setText(
                ', '.join([str(v) for v in settings.plot['mask_val']]))

        # Emit signal to trigger plot updates/etc
        if emit:
            self.plot_options_changed.emit()

    def _init_plot_options(self):
        logger.debug('Initializing plot options')
        # Click point, add layer
        self.cbox_plotlayer.setChecked(settings.plot['plot_layer'])  # TODO: wire

        # Band select
        self.combox_band.clear()

        model = QtGui.QStandardItemModel(1 + len(settings.plot_bands), 1)
        item = QtGui.QStandardItem('----- Select Plot Band -----')
        item.setTextAlignment(QtCore.Qt.AlignHCenter)
        item.setSelectable(False)
        model.setItem(0, 0, item)

        for i, name in enumerate(settings.plot_bands):
            item = QtGui.QStandardItem(u'☐: ' + name)
            item.setSelectable(False)
            model.setItem(i + 1, 0, item)
        self.combox_band.setModel(model)
        self.combox_band.view().pressed.connect(self._band_combox_pressed)

        # Y-axis selector
        axis = settings.plot['axis_select']
        if axis == 0:
            self.rad_axis_1.setChecked(True)
            self.rad_axis_2.setChecked(False)
        elif axis == 1:
            self.rad_axis_1.setChecked(False)
            self.rad_axis_2.setChecked(True)
        self.rad_axis_1.toggled.connect(self._plot_y_axis_changed)
        self.rad_axis_2.toggled.connect(self._plot_y_axis_changed)

        self.cbox_yscale_auto.setChecked(
            settings.plot['y_axis_scale_auto'][axis])
        self.cbox_yscale_auto.stateChanged.connect(self.plot_option_changed)

        # Y-axis min/max
        self.edit_ymin.setText(str(settings.plot['y_min'][axis]))
        self.edit_ymax.setText(str(settings.plot['y_max'][axis]))
        self.edit_ymin.editingFinished.connect(self.plot_option_changed)
        self.edit_ymax.editingFinished.connect(self.plot_option_changed)
        self.edit_ymin.setEnabled(not settings.plot['y_axis_scale_auto'][axis])
        self.edit_ymax.setEnabled(not settings.plot['y_axis_scale_auto'][axis])

        # X-axis
        self.cbox_xscale_fix.setChecked(settings.plot['x_scale_fix'])
        self.cbox_xscale_fix.stateChanged.connect(self._xrange_fixed)

        self.lab_xmin.setText(str(settings.plot['x_min']))
        self.lab_xmax.setText(str(settings.plot['x_max']))

        self.scroll_xmin.setRange(settings.plot['x_min'],
                                  settings.plot['x_max'] - 1)
        self.scroll_xmax.setRange(settings.plot['x_min'] + 1,
                                  settings.plot['x_max'])
        self.scroll_xmin.setValue(settings.plot['x_min'])
        self.scroll_xmax.setValue(settings.plot['x_max'])
        self.scroll_xmin.valueChanged.connect(
            partial(self._xrange_changed, 'min'))
        self.scroll_xmax.valueChanged.connect(
            partial(self._xrange_changed, 'max'))
        self.scroll_xmin.sliderMoved.connect(
            partial(self._xrange_moved, 'min'))
        self.scroll_xmax.sliderMoved.connect(
            partial(self._xrange_moved, 'max'))

        # Plot features
        self.cbox_fmask.setChecked(settings.plot['mask'])
        self.cbox_fmask.stateChanged.connect(self.plot_option_changed)

        if settings.plot['mask_val'] is not None:
            self.edit_maskvalues.setText(
                ', '.join(map(str, settings.plot['mask_val'])))
        else:
            self.edit_maskvalues.setText('')
        self.edit_maskvalues.editingFinished.connect(self.plot_option_changed)

        if tsm.ts.has_results is True:
            self.cbox_modelfit.setEnabled(True)
            self.cbox_modelfit.setChecked(settings.plot['fit'])
            self.cbox_modelfit.stateChanged.connect(self.plot_option_changed)

            self.cbox_breakpoint.setEnabled(True)
            self.cbox_breakpoint.setChecked(settings.plot['break'])
            self.cbox_breakpoint.stateChanged.connect(self.plot_option_changed)
        else:
            self.cbox_modelfit.setChecked(False)
            self.cbox_modelfit.setEnabled(False)
            self.cbox_breakpoint.setChecked(False)
            self.cbox_breakpoint.setEnabled(False)

        # Symbology
        if hasattr(self, 'symbology_controls'):
            self.symbology_controls.disconnect()
            self.symbology_controls = None
        self.symbology_controls = SymbologyControl(self)
        self.but_symbology.clicked.connect(
            lambda: self.symbology_controls.show())
        self.symbology_controls.plot_symbology_applied.connect(
            lambda: self.plot_options_changed.emit())

        # Plot save
        def _close_save_plot(self):
            self.save_plot_dialog.save_plot_requested.disconnect()
            self.save_plot_dialog.save_plot_closed.disconnect()
            self.save_plot_dialog.close()

        self.save_plot_dialog = SavePlotDialog(self)
        self.save_plot_dialog.save_plot_requested.connect(
            lambda: self.plot_save_requested.emit())
        self.save_plot_dialog.save_plot_closed.connect(
            partial(_close_save_plot, self))
        self.but_plot_save.clicked.connect(
            lambda: self.save_plot_dialog.exec_())

# IMAGE TABLE
    def _init_table(self):
        logger.debug('Initializing images tables')
        self.image_tables = []

        # Series controller
        self.combox_table_series.clear()
        self.combox_table_series.addItems([series.description for
                                           series in tsm.ts.series])

        # Clear stacked widget
        for i in range(self.stacked_table.count()):
            self.stacked_table.removeWidget(self.stacked_table.widget(i))

        # Add tables
        for i, series in enumerate(tsm.ts.series):
            # Setup table
            table = QtGui.QTableWidget()
            table.verticalHeader().setVisible(False)

            # Setup headers
            headers = ['ID', 'Date']
            extra_metadata = []

            if (hasattr(series, 'metadata')
                    and hasattr(series, 'metadata_table')
                    and hasattr(series, 'metadata_names')):
                for md, md_str, md_bool in zip(series.metadata,
                                               series.metadata_names,
                                               series.metadata_table):
                    if md_bool is True:
                        logger.debug('Adding TS driver supplied metadata: '
                                     '{m}'.format(m=md_str))
                        headers.append(md_str)
                        extra_metadata.append(getattr(series, md))

            table.setColumnCount(len(headers))
            table.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOn)
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setResizeMode(
                QtGui.QHeaderView.Stretch)
            table.resizeColumnsToContents()

            # Populate table
            table.setRowCount(len(series.images['id']))
            for row in range(len(series.images['id'])):
                _cbox = QtGui.QTableWidgetItem()
                _cbox.setFlags(QtCore.Qt.ItemIsUserCheckable |
                               QtCore.Qt.ItemIsEnabled)
                _cbox.setCheckState(QtCore.Qt.Unchecked)
                _cbox.setText(series.images['id'][row])
                _cbox.setTextAlignment(QtCore.Qt.AlignHCenter |
                                       QtCore.Qt.AlignVCenter)

                _date = QtGui.QTableWidgetItem(
                    series.images['date'][row].strftime('%Y-%j'))
                _date.setFlags(QtCore.Qt.ItemIsEnabled)
                _date.setTextAlignment(QtCore.Qt.AlignHCenter |
                                       QtCore.Qt.AlignVCenter)

                table.setItem(row, 0, _cbox)
                table.setItem(row, 1, _date)

                # Driver supplied metadata
                for i, md in enumerate(extra_metadata):
                    _item = QtGui.QTableWidgetItem(str(md[row]))
                    _item.setFlags(QtCore.Qt.ItemIsEnabled)
                    _item.setTextAlignment(QtCore.Qt.AlignHCenter |
                                           QtCore.Qt.AlignVCenter)
                    table.setItem(row, 2 + i, _item)

            # Wire signal to `self.image_table_row_clicked`
            @QtCore.pyqtSlot()
            def _image_table_clicked(self, item):
                if item.column() == 0:
                    logger.info('Clicked row: {r}'.format(r=item.row()))
                    self.image_table_row_clicked.emit(item.row())
            table.itemClicked.connect(
                partial(_image_table_clicked, self))

            # Add and store reference to table
            self.stacked_table.insertWidget(i, table)
            self.image_tables.append(table)

        self.stacked_table.setCurrentIndex(0)

# SYMBOLOGY
    def _init_symbology(self):
        logger.debug('Initializing symbology')
        self.symbologies = []
        # Control symbology
        self.cbox_symbolcontrol.setChecked(settings.symbol_control)
        self.cbox_symbolcontrol.stateChanged.connect(self._set_symbol_control)

        # Series controller
        self.combox_symbology_series.clear()
        self.combox_symbology_series.addItems([series.description for
                                               series in tsm.ts.series])

        # Add symbology widgets for each Series
        for i, series in enumerate(tsm.ts.series):
            # Setup UI
            symbol = RasterSymbologyControl(self.iface)
            symbol.init_ts(i, series)

            # Add and store reference to widget
            self.stacked_symbology.insertWidget(i, symbol)
            self.symbologies.append(symbol)

        self.stacked_symbology.setCurrentIndex(0)

        # Setup and wire "Apply" button
        self.but_symbol_apply.setEnabled(settings.symbol_control)
        self.but_symbol_apply.clicked.connect(
            lambda: self.symbology_applied.emit())

    @QtCore.pyqtSlot()
    def _set_symbol_control(self, state):
        if state == QtCore.Qt.Checked:
            settings.symbol_control = True
            self.but_symbol_apply.setEnabled(True)
        elif state == QtCore.Qt.Unchecked:
            settings.symbol_control = False
            self.but_symbol_apply.setEnabled(False)

# CUSTOM OPTIONS
    def _init_custom_controls(self):
        if not (getattr(tsm.ts, 'controls', None) and
                getattr(tsm.ts, 'controls_title', None) and
                getattr(tsm.ts, 'controls_names', None)):
            logger.debug('No custom controls to initialize')
            return
        if not hasattr(tsm.ts, 'set_custom_controls'):
            logger.info('Timeseries driver has controls but no setter method')
            return

        logger.debug('Initializing custom controls')
        config = OrderedDict([
            [var, [name, getattr(tsm.ts, var)]] for var, name in
            zip(tsm.ts.controls, tsm.ts.controls_names)
        ])
        self.custom_form = CustomForm(config)
        self.tab_options.layout().addWidget(self.custom_form)

# DISCONNECT SIGNALS
    def disconnect(self):
        """ Disconnect all signals
        """
        self.cbox_plotlayer.disconnect()
        # Plot options
        self.combox_band.disconnect()
        self.rad_axis_1.disconnect()
        self.rad_axis_2.disconnect()
        self.cbox_yscale_auto.disconnect()
        self.edit_ymin.disconnect()
        self.edit_ymax.disconnect()
        self.scroll_xmin.disconnect()
        self.scroll_xmax.disconnect()
        self.cbox_xscale_fix.disconnect()
        self.cbox_fmask.disconnect()
        self.edit_maskvalues.disconnect()
        self.cbox_modelfit.disconnect()
        self.cbox_breakpoint.disconnect()

        self.but_symbology.disconnect()
        self.symbology_controls.disconnect()
        self.symbology_controls.deleteLater()
        self.symbology_controls = None

        self.but_plot_save.disconnect()
        self.save_plot_dialog.disconnect()
        self.save_plot_dialog.deleteLater()
        self.save_plot_dialog = None

        # Table
        for table in self.image_tables:
            table.disconnect()

        # Symbology
        self.cbox_symbolcontrol.disconnect()
        for symbology in self.symbologies:
            symbology.disconnect()
        self.but_symbol_apply.disconnect()

        # Custom options -- remove them
        self.custom_form = getattr(self, 'custom_form', None)
        if self.custom_form:
            logger.debug('Deleting pre-existing custom options')
            self.custom_form.deleteLater()
            self.tab_options.layout().removeWidget(self.custom_form)
            self.custom_form = None
