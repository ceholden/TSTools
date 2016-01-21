""" QDialog for setting plot symbology based on qualitative data
"""
from collections import OrderedDict
import copy
from functools import partial
import logging

from PyQt4 import QtCore, QtGui

import matplotlib as mpl
import numpy as np

from ..ui_plot_symbology import Ui_Plot_Symbology

from .attach_md import AttachMetadata

from .. import settings
from ..ts_driver.ts_manager import tsm
from ..utils import ravel_series_band

logger = logging.getLogger('tstools')


class SymbologyControl(QtGui.QDialog, Ui_Plot_Symbology):

    """ Plot symbology controls
    """

    plot_symbology_applied = QtCore.pyqtSignal()

    def __init__(self, iface):
        # Qt setup
        self.iface = iface
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

        # Setup matplotlib markers
        keys = [k for k in mpl.lines.Line2D.markers.keys()
                if len(str(k)) == 1 and k != ' ']
        marker_texts = ['{k} - {v}'.format(k=k, v=mpl.lines.Line2D.markers[k])
                        for k in keys]
        self.markers = {k: text for k, text in zip(keys, marker_texts)}

        self.default_sym = dict(marker=settings.default_plot_symbol['markers'],
                                color=settings.default_plot_symbol['colors'])

        # Finish setting up GUI
        self.setup()

    def setup(self):
        """ Setup GUI with metadata from timeseries
        """
        # Find unique values to store in `self.md`
        self._init_metadata()

        # Store band lists and stack widgets
        self.list_bands = []  # [series]
        self.combox_metadata = []  # [series][band]
        self.stack_metadata_items = []  # [series][band]
        self.combox_markers = {}  # [series][band][metadata]
        self.but_colors = {}  # [series][band][metadata]

        # Setup series and band QComboBoxes
        self.combox_series.clear()
        self.combox_series.addItems([s.description for s in tsm.ts.series])
        self.combox_series.currentIndexChanged.connect(
            self._change_series)

        n = 1
        for i, series in enumerate(tsm.ts.series):
            # Populate band selection stack widget
            qlist = QtGui.QListWidget()
            qlist.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
            qlist.setAlternatingRowColors(True)
            qlist.addItems(series.band_names)
            qlist.itemSelectionChanged.connect(partial(self._change_band, i))

            self.stack_band.insertWidget(i, qlist)
            self.list_bands.append(qlist)

            # Setup metadata combo box and metadata table
            _stack_bands = []
            _combox_metadata = []
            _combox_markers = {}
            _but_colors = {}
            for j, band in enumerate(series.band_names):
                widget = QtGui.QWidget()
                layout = QtGui.QVBoxLayout()

                # Add a copy of all metadata items in series for each band
                md_combox = QtGui.QComboBox()
                md_combox.addItems(self.md[i][j].keys())
                md_combox.currentIndexChanged.connect(
                    partial(self._change_md, i))
                layout.addWidget(md_combox)
                _combox_metadata.append(md_combox)

                stack = QtGui.QStackedWidget()
                # Add tables of all metadata items to QStackWidget
                __combox_markers = {}
                __but_colors = {}
                for k, (item, vals) in enumerate(self.md[i][j].iteritems()):
                    table, comboxes, buts = self._setup_metadata_table(
                        i, j, item, vals)
                    stack.insertWidget(k, table)
                    __combox_markers[item] = comboxes
                    __but_colors[item] = buts

                _stack_bands.append(stack)
                _combox_markers[j] = __combox_markers
                _but_colors[j] = __but_colors

                stack.setCurrentIndex(0)
                layout.addWidget(stack)

                widget.setLayout(layout)
                self.stack_metadata.insertWidget(n, widget)
                n += 1

            self.stack_metadata_items.append(_stack_bands)
            self.combox_metadata.append(_combox_metadata)
            self.combox_markers[i] = _combox_markers
            self.but_colors[i] = _but_colors

        self.stack_band.setCurrentIndex(0)
        self.stack_metadata.setCurrentIndex(0)

        self.button_box.button(QtGui.QDialogButtonBox.Apply).clicked.connect(
            self._apply_symbology)

    def _init_metadata(self):
        """ Finds unique values for each metadata item and sets up symbology
        """
        self.md = OrderedDict()  # {series}{band}{metadata}{value}
        for i, series in enumerate(tsm.ts.series):
            self.md[i] = OrderedDict()
            for j, band in enumerate(series.band_names):
                item = OrderedDict()
                # Setup default (no metadata)
                idx = ravel_series_band(i, j)
                idx_default_sym = {
                    'color': settings.plot_symbol[idx]['colors'][0],
                    'marker': settings.plot_symbol[idx]['markers'][0]
                }
                item['Default'] = {
                    None: copy.deepcopy(idx_default_sym)
                }

                # If has metadata, add that in too
                if (hasattr(series, 'metadata') and
                        hasattr(series, 'metadata_names')):
                    for _md, _md_str in zip(series.metadata,
                                            series.metadata_names):
                        vals = OrderedDict()
                        for uniq in np.unique(getattr(series, _md)):
                            vals[uniq] = copy.deepcopy(idx_default_sym)
                        item[_md_str] = copy.deepcopy(vals)

                self.md[i][j] = copy.deepcopy(item)

    def _setup_metadata_table(self, series, band, md_item, values):
        """ Add QTableWidgets containing metadata for each metadata item
        """
        # Setup table
        table = QtGui.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Value', 'Marker', 'Color'])
        table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        table.setRowCount(len(values.keys()))

        comboxes = {}
        buts = {}
        for i, (val, sym) in enumerate(values.iteritems()):
            # Value label
            lab = QtGui.QLabel(str(val))
            lab.setAlignment(QtCore.Qt.AlignCenter)

            # Marker
            combox = QtGui.QComboBox()
            combox.addItems(self.markers.values())
            combox.setCurrentIndex(
                combox.findText(self.markers[sym['marker']]))
            combox.currentIndexChanged.connect(
                partial(self._change_marker, series, md_item, val))
            comboxes[val] = combox

            # Color button
            but = QtGui.QPushButton('Color')
            but.setAutoFillBackground(True)
            self._set_button_color(but, sym['color'])
            but.clicked.connect(
                partial(self._change_color, series, band, md_item, val))
            buts[val] = but

            # Add to table
            table.setCellWidget(i, 0, lab)
            table.setCellWidget(i, 1, combox)
            table.setCellWidget(i, 2, but)

        table.resizeColumnsToContents()

        return table, comboxes, buts

# SLOTS
    @QtCore.pyqtSlot(int)
    def _change_series(self, index):
        """ Change bands, metadata, and symbology based on series """
        logger.debug('Series selected {s}'.format(s=index))
        # Switch band stack to series' bands
        self.stack_band.setCurrentIndex(index)
        # Switch metadata stack to series' selected bands' metadata
        self._change_band(index)

    @QtCore.pyqtSlot(int, int)
    def _change_band(self, idx):
        """ Change metadata table based on currently selected band """
        selected = self.list_bands[idx].selectedItems()
        if not selected:
            self.stack_metadata.setCurrentIndex(0)
        else:
            logger.debug('Selected rows: {s}'.format(
                s=[self.list_bands[idx].row(s) for s in selected]))
            i_series = self.combox_series.currentIndex()
            i_band = self.list_bands[idx].row(selected[0])

            self.stack_metadata.setCurrentWidget(
                self.stack_metadata_items[i_series][i_band].parentWidget())

    @QtCore.pyqtSlot(int)
    def _change_md(self, series, idx):
        for selected in self.list_bands[series].selectedItems():
            band = self.list_bands[series].row(selected)
            logger.debug('Changing metadata to: {md}'.format(
                md=self.md[series][band].keys()[idx]))
            self.stack_metadata_items[series][band].setCurrentIndex(idx)
            # Block signal from changing metadata QComboBox
            self.combox_metadata[series][band].blockSignals(True)
            self.combox_metadata[series][band].setCurrentIndex(idx)
            self.combox_metadata[series][band].blockSignals(False)

    @QtCore.pyqtSlot(int)
    def _change_marker(self, series, md_item, value, idx):
        for selected in self.list_bands[series].selectedItems():
            band = self.list_bands[series].row(selected)
            logger.debug('Changing marker from {f} to {t}'.format(
                f=self.md[series][band][md_item][value], t=idx))
            # Block signal when changing metadata marker
            self.combox_markers[series][band][
                md_item][value].blockSignals(True)
            self.combox_markers[series][band][
                md_item][value].setCurrentIndex(idx)
            self.combox_markers[series][band][
                md_item][value].blockSignals(False)
            self.md[series][band][md_item][value]['marker'] = \
                self.markers.keys()[idx]

    @QtCore.pyqtSlot()
    def _change_color(self, series, band, md_item, value):
        logger.debug('Changing color')
        col = self.md[series][band][md_item][value]['color']
        col = QtGui.QColor(col[0], col[1], col[2])

        color_dialog = QtGui.QColorDialog()
        new_col = color_dialog.getColor(
            col, self, 'Pick color for {u}'.format(u=value))

        if not new_col.isValid():
            return

        for selected in self.list_bands[series].selectedItems():
            band = self.list_bands[series].row(selected)
            but = self.but_colors[series][band][md_item][value]

            self.md[series][band][md_item][value]['color'] = [
                new_col.red(), new_col.green(), new_col.blue()]
            self._set_button_color(
                but, self.md[series][band][md_item][value]['color'])

    @QtCore.pyqtSlot()
    def _apply_symbology(self):
        """ Forward current symbology from here to settings and emit update """
        logger.debug('Applying symbology')
        self._update_metadata()
        self.plot_symbology_applied.emit()

# UTILITY
    def _update_metadata(self):
        for i, series in enumerate(tsm.ts.series):
            for j, band in enumerate(series.band_names):
                idx = ravel_series_band(i, j)
                md = self.combox_metadata[i][j].currentText()

                if md == 'Default':
                    # Default -- just on index
                    n_image = series.images.shape[0]
                    settings.plot_symbol[idx]['indices'] = [np.arange(n_image)]
                    settings.plot_symbol[idx]['markers'] = [
                        self.md[i][j][md][None]['marker']]
                    settings.plot_symbol[idx]['colors'] = [
                        self.md[i][j][md][None]['color']]
                else:
                    # Otherwise, index based on dataset values
                    md_i = [_i for _i, name in enumerate(series.metadata_names)
                            if name == md][0]
                    dat = getattr(series, series.metadata[md_i])
                    # For each metadata item value, find index and
                    #   assign marker and color
                    indices = []
                    markers = []
                    colors = []
                    for k, val in self.md[i][j][md].iteritems():
                        # TODO: we don't always need to update index,
                        #   and this might be expensive
                        indices.append(np.where(dat == k)[0])
                        markers.append(val['marker'])
                        colors.append(val['color'])
                    settings.plot_symbol[idx]['indices'] = indices
                    settings.plot_symbol[idx]['markers'] = markers
                    settings.plot_symbol[idx]['colors'] = colors

    def _set_button_color(self, but, col):
        """ Sets color for a QPushButton """
        c_str = 'rgb({r}, {g}, {b})'.format(r=col[0], g=col[1], b=col[2])
        style = 'QPushButton {{color: {c}; font-weight: bold}}'.format(c=c_str)

        but.setStyleSheet(style)

# CLEANUP
    def disconnect(self):
        # TODO: finish disconnect
        self.combox_series.currentIndexChanged.disconnect()
