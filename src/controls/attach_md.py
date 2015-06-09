# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 TSTools metadata plotter helper widget
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
import logging
import os

from PyQt4 import QtCore, QtGui

import numpy as np

from ..ui_attach_md import Ui_AttachMd

from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


class AttachMetadata(QtGui.QDialog, Ui_AttachMd):
    """ Plot symbology metadata attacher """

    metadata_attached = QtCore.pyqtSignal()

    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

        # Metadata file
        self.metadata_file = os.getcwd()
        self.metadata_header = True
        self.metadata_delim = ','

        self.md = None
        self.colnames = None

        # Finish setup
        self.setup_gui()

    def setup_gui(self):
        """ Finish initializing GUI """
        # Open metadata GUI
        self.edit_metadata.setText(self.metadata_file)
        self.edit_delim.setText(self.metadata_delim)
        self.cbox_header.setChecked(QtCore.Qt.Checked if self.metadata_header
                                    else QtCore.Qt.Unchecked)

        self.but_browse.clicked.connect(self.find_metadata)
        self.but_load.clicked.connect(self.load_metadata)

        # Match buttons
        self.match_buttons = QtGui.QButtonGroup()
        self.match_buttons.addButton(self.rad_ID)
        self.match_buttons.addButton(self.rad_date)
        self.rad_ID.setChecked(True)

        # Add metadata button
        self.but_add_metadata.clicked.connect(self.add_metadata)

    @QtCore.pyqtSlot()
    def find_metadata(self):
        """ Open QFileDialog to find a metadata file """
        # Open QFileDialog
        metadata = str(QtGui.QFileDialog.getOpenFileName(self,
            'Locate metadata file',
            self.metadata_file if os.path.isdir(self.metadata_file)
            else os.path.dirname(self.metadata_file)))

        if metadata != '':
            self.edit_metadata.setText(metadata)

    @QtCore.pyqtSlot()
    def load_metadata(self):
        """ Try to load metadata file specified by QLineEdit

        Wraps `self.try_load_metadata` by handling rest of GUI after
        success/failure
        """
        # Try to open metadata file
        success = self.try_load_metadata()

        if success:
            self.rad_ID.setEnabled(True)
            self.rad_date.setEnabled(True)
            self.table_metadata.setEnabled(True)
        else:
            self.rad_ID.setEnabled(False)
            self.rad_date.setEnabled(False)
            self.table_metadata.setEnabled(False)
            return

        # Load table with metadata
        self.table_metadata.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectColumns)
        self.table_metadata.setColumnCount(len(self.colnames))
        self.table_metadata.setRowCount(self.md.shape[0])

        self.table_metadata.setHorizontalHeaderLabels(self.colnames)
        for (r, c), v in np.ndenumerate(self.md):
            item = QtGui.QTableWidgetItem(str(v))
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.table_metadata.setItem(r, c, item)

        self.table_metadata.selectColumn(0)

    def try_load_metadata(self):
        """ Try to load metadata file specified by QLineEdit """
        # Get current value
        metadata = str(self.edit_metadata.text())
        # Get delimiter
        delim = str(self.edit_delim.text())
        # Get header indicator
        header = (True if self.cbox_header.checkState() == QtCore.Qt.Checked
                  else False)

        # Try to open
        try:
            md = np.genfromtxt(metadata, dtype=str, delimiter=delim,
                               skip_header=1 if header else 0,
                               autostrip=True)
        except:
            qgis_log('Could not parse metadata file',
                     level=logging.WARNING, duration=5)
            raise
            return False

        if header:
            try:
                with open(metadata, 'r') as f:
                    colnames = f.readline().split(delim)
            except:
                qgis_log('Could not parse metadata header',
                         logging.WARNING, 5)
                raise
                return False
        else:
            colnames = ['Column ' + str(i + 1) for i in range(md.shape[1])]

        if not len(colnames) == md.shape[1]:
            msg = ('Metadata file has more column headers ({c})'
                   ' than fields ({f})'.format(c=len(colnames), f=md.shape[1]))
            qgis_log(msg, logging.WARNING, 5)
            return False

        self.metadata_file = metadata
        self.md = md
        self.colnames = list(colnames)

        return True

    @QtCore.pyqtSlot()
    def add_metadata(self):
        """ """
        # Try to match metadata
        ts_match_var = (tsm.ts.images['id'] if self.rad_ID.isChecked() is True
                        else tsm.ts.images['date'])
        # Match column
        match_col = self.table_metadata.selectedItems()[0].column()
        md_match_var = self.md[:, match_col]

        # Try to match
        if len(ts_match_var) != len(md_match_var):
            msg = 'Wrong number of elements to match ({t} vs. {m})'.format(
                t=len(ts_match_var), m=len(md_match_var))
            qgis_log(msg, logging.WARNING, 5)
            return

        if not np.all(np.sort(ts_match_var) == np.sort(md_match_var)):
            msg = 'Not all elements match'
            qgis_log(msg, logging.WARNING, 5)
            return

        # Perform match
        match_ind = []
        for i in xrange(len(ts_match_var)):
            ind = np.where(md_match_var == ts_match_var[i])[0]
            if len(ind) > 1:
                msg = 'Multiple index matches for {m}'.format(
                    m=ts_match_var[i])
                qgis_log(msg, logging.WARNING, 5)
                return
            match_ind.append(ind[0])
        match_ind = np.array(match_ind)

        # Sort
        self.md_sorted = self.md[match_ind, :]

        # Add to timeseries
        for i, md in enumerate(self.colnames):
            # Ignore match column
            if i == match_col:
                continue
            if md not in tsm.ts.metadata and not hasattr(tsm.ts, md):
                tsm.ts.metadata.append(md)
                tsm.ts.metadata_str.append(md)
                setattr(tsm.ts, md, self.md_sorted[:, i])
            else:
                msg = 'TS already has metadata item {m}'.format(m=md)
                qgis_log(msg, logging.WARNING, 5)

        # Emit
        self.metadata_attached.emit()
