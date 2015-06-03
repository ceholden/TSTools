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
from functools import partial
import logging

from PyQt4 import QtCore, QtGui

import numpy as np

from ui_controls import Ui_Controls as Ui_Widget

from . import settings
from .logger import qgis_log
from .ts_driver.ts_manager import tsm
from .controls_symbology import SymbologyControl
from .save_plot_dialog import SavePlotDialog

logger = logging.getLogger('tstools')


def str2num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


class ControlPanel(QtGui.QWidget, Ui_Widget):

    plot_options_changed = QtCore.pyqtSignal()
    plot_save_requested = QtCore.pyqtSignal()

    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QtGui.QWidget.__init__(self)
        self.setupUi(self)

    def init_ts(self):
        self._init_plot_options()

# PLOT TAB
    @QtCore.pyqtSlot(int)
    def _band_combox_pressed(self, index):
        # Do not run for "Select Plot Band" (first QComboBox item)
        if index == 0:
            return

        item = self.combox_band.model().itemFromIndex(index)
        index = index.row() - 1
        name = tsm.ts.band_names[index]

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

        self.plot_options_changed.emit()

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
    def _plot_option_changed(self):
        """ Catch all slot for plot control panel changes
        """
        logger.debug('Updating plot options')
        # Y-axis
        settings.plot['axis_select'] = 0 if self.rad_axis_1.isChecked() else 1
        settings.plot['y_scale_auto'] = \
            True if self.cbox_yscale_auto.isChecked() else False
        settings.plot['y_min'][settings.plot['axis_select']] = \
            str2num(self.edit_ymin.text())
        settings.plot['y_max'][settings.plot['axis_select']] = \
            str2num(self.edit_ymax.text())

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
        self.plot_options_changed.emit()

    def _init_plot_options(self):
        logger.debug('Initializing plot options')
        # Click point, add layer
        self.cbox_plotlayer.setChecked(settings.plot['plot_layer'])

        # Band select
        self.combox_band.clear()

        model = QtGui.QStandardItemModel(1 + len(tsm.ts.band_names), 1)
        item = QtGui.QStandardItem('----- Select Plot Band -----')
        item.setTextAlignment(QtCore.Qt.AlignHCenter)
        item.setSelectable(False)
        model.setItem(0, 0, item)

        for i, name in enumerate(tsm.ts.band_names):
            item = QtGui.QStandardItem(u'☐: ' + name)
            item.setSelectable(False)
            model.setItem(i + 1, 0, item)
        self.combox_band.setModel(model)
        self.combox_band.view().pressed.connect(self._band_combox_pressed)

        # Y-axis selector
        if settings.plot['axis_select'] == 0:
            self.rad_axis_1.setChecked(True)
            self.rad_axis_2.setChecked(False)
        else:
            self.rad_axis_1.setChecked(False)
            self.rad_axis_2.setChecked(True)
        self.rad_axis_1.toggled.connect(self._plot_option_changed)
        self.rad_axis_2.toggled.connect(self._plot_option_changed)

        # Y-axis min/max
        self.edit_ymin.setText(str(
            settings.plot['y_min'][settings.plot['axis_select']]))
        self.edit_ymax.setText(str(
            settings.plot['y_max'][settings.plot['axis_select']]))
        self.edit_ymin.editingFinished.connect(self._plot_option_changed)
        self.edit_ymax.editingFinished.connect(self._plot_option_changed)

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
        self.cbox_fmask.stateChanged.connect(self._plot_option_changed)

        if settings.plot['mask_val'] is not None:
            self.edit_maskvalues.setText(
                ', '.join(map(str, settings.plot['mask_val'])))
        else:
            self.edit_maskvalues.setText('')
        self.edit_maskvalues.editingFinished.connect(self._plot_option_changed)

        if tsm.ts.has_results is True:
            self.cbox_modelfit.setEnabled(True)
            self.cbox_modelfit.setChecked(settings.plot['fit'])
            self.cbox_modelfit.stateChanged.connect(self.set_model_fit)

            self.cbox_breakpoint.setEnabled(True)
            self.cbox_breakpoint.setChecked(settings.plot['break'])
            self.cbox_breakpoint.stateChanged.connect(self.set_break_point)
        else:
            self.cbox_modelfit.setChecked(False)
            self.cbox_modelfit.setEnabled(False)
            self.cbox_breakpoint.setChecked(False)
            self.cbox_breakpoint.setEnabled(False)

        # Symbology
        self.symbology_controls = SymbologyControl(self)
        self.symbology_controls.setup_gui()
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

    def disconnect(self):
        """ Disconnect all signals
        """
        self.but_symbology.disconnect()
        self.symbology_controls.disconnect()
        self.symbology_controls.deleteLater()
        self.symbology_controls = None

        self.but_plot_save.disconnect()
        self.save_plot_dialog.disconnect()
        self.save_plot_dialog.deleteLater()
        self.save_plot_dialog = None
