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
from PyQt4 import QtCore
from PyQt4 import QtGui

from functools import partial

import numpy as np
import matplotlib as mpl

from ui_symbology import Ui_Symbology as Ui_Widget
import settings as setting


class SymbologyControl(QtGui.QDialog, Ui_Widget):
    """ Plot symbology controls """

    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

        keys = [k for k in mpl.lines.Line2D.markers.keys()
                if len(str(k)) == 1 and k != ' ']
        marker_texts = ['{k} - {v}'.format(k=k, v=mpl.lines.Line2D.markers[k])
                        for k in keys]

        self.markers = {k: text for k, text in zip(keys, marker_texts)}

    def setup_gui(self, ts):
        """ Setup GUI with metadata from timeseries """
        # Check for metadata
        md = getattr(ts, '__metadata__', None)
        if not isinstance(md, list) or len(md) == 0:
            self.has_metadata = False
            self.setup_gui_nomd()
            return
        self.md = [getattr(ts, _md) for _md in md]

        self.has_metadata = True

        # Setup metadata listing
        md_str = getattr(ts, '__metadata__str__', None)
        if not isinstance(md_str, list) or len(md_str) != len(self.md):
            # If there is no description string, just use variable names
            md_str = md

        for _md_str in md_str:
            self.list_metadata.addItem(QtGui.QListWidgetItem(_md_str))
        self.list_metadata.setCurrentRow(0)

        # Find all unique values for all metadata items
        self.unique_values = []
        for _md in self.md:
            self.unique_values.append(np.unique(_md))

        # Init marker and color for unique values in all metadatas
        self.unique_symbologies = []
        for md in self.unique_values:
            color = [0, 0, 0]
            marker = '.'
            unique_md = {}
            for unique in md:
                unique_md[unique] = {'color': color,
                                     'marker': marker
                                     }
            self.unique_symbologies.append(unique_md)

        # Setup initial set of symbology for item selected
        self.tables = []
        for i_md, unique_values in enumerate(self.unique_values):
            self.init_metadata(i_md)
        self.stack_widget.setCurrentIndex(0)

        # Add handler for stacked widget
        self.list_metadata.currentRowChanged.connect(self.metadata_changed)

    def init_metadata(self, i_md):
        """ Initialize symbology table with selected metadata attributes """
        if not self.has_metadata:
            return

        # Add QTableWidget
        table = QtGui.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Value', 'Marker', 'Color'])
        table.horizontalHeader().setStretchLastSection(True)

        table.setRowCount(len(self.unique_values[i_md]))

        # Populate table
        for i, unique in enumerate(self.unique_values[i_md]):
            # Fetch current values
            color = self.unique_symbologies[i_md][unique]['color']
            marker = self.unique_symbologies[i_md][unique]['marker']

            # Label for value
            lab = QtGui.QLabel(str(unique))
            lab.setAlignment(QtCore.Qt.AlignCenter)

            # Possible markers in combobox
            cbox = QtGui.QComboBox()
            for m in self.markers.values():
                cbox.addItem(m)
            cbox.setCurrentIndex(cbox.findText(self.markers[marker]))

            # Colors
            button = QtGui.QPushButton('Color')
            button.setAutoFillBackground(True)
            self.set_button_color(button, color)

            button.pressed.connect(partial(self.color_button_pressed,
                                           i, i_md, unique))

            # Add to table
            table.setCellWidget(i, 0, lab)
            table.setCellWidget(i, 1, cbox)
            table.setCellWidget(i, 2, button)

        self.tables.append(table)
        self.stack_widget.insertWidget(i_md, table)

    @QtCore.pyqtSlot()
    def color_button_pressed(self, i, i_md, unique):
        """ """
        # Current color
        c = self.unique_symbologies[i_md][unique]['color']
        current_c = QtGui.QColor(c[0], c[1], c[2])

        # Get new color
        color_dialog = QtGui.QColorDialog()

        new_c = color_dialog.getColor(current_c, self,
                                      'Pick color for {u}'.format(u=unique))
        if not new_c.isValid():
            return

        # Update color and button
        self.unique_symbologies[i_md][unique]['color'] = [new_c.red(),
                                                          new_c.green(),
                                                          new_c.blue()
                                                          ]
        button = self.tables[i_md].cellWidget(i, 2)

        self.set_button_color(button,
                              self.unique_symbologies[i_md][unique]['color'])

    @QtCore.pyqtSlot(int)
    def metadata_changed(self, row):
        """ Switch metadata tables """
        self.stack_widget.setCurrentIndex(row)

    def set_button_color(self, button, c):
        """ Sets button text color """
        c_str = 'rgb({r}, {g}, {b})'.format(r=c[0], g=c[1], b=c[2])
        style = 'QPushButton {{color: {c}; font-weight: bold}}'.format(c=c_str)

        button.setStyleSheet(style)

    def setup_gui_nomd(self):
        """ Setup GUI if timeseries has no metadata """
        item = QtGui.QListWidgetItem('No Metadata')
        self.list_metadata.addItem(item)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
