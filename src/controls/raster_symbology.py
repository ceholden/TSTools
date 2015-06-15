from functools import partial
import logging

from PyQt4 import QtCore, QtGui

from ..ui_raster_symbology import Ui_Raster_Symbology

from .. import settings
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


def str2num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


class RasterSymbologyControl(QtGui.QWidget, Ui_Raster_Symbology):
    """ Raster symbology controls """

    def __init__(self, iface):
        self.iface = iface
        QtGui.QWidget.__init__(self)
        self.setupUi(self)

    def init_ts(self, index, series):
        # Store reference to index and series
        self.index = index
        self.series = series

        # Band selections
        self.combox_red.clear()
        self.combox_red.addItems(self.series.band_names)
        self.combox_red.setCurrentIndex(
            settings.symbol[self.index]['band_red'])
        self.combox_green.clear()
        self.combox_green.addItems(self.series.band_names)
        self.combox_green.setCurrentIndex(
            settings.symbol[self.index]['band_green'])
        self.combox_blue.clear()
        self.combox_blue.addItems(self.series.band_names)
        self.combox_blue.setCurrentIndex(
            settings.symbol[self.index]['band_blue'])

        # Band min/max
        self.update_minmax_text()

        # Contrast enhancement
        self.combox_cenhance.setCurrentIndex(
            settings.symbol[self.index]['contrast'])

        # Add signals
        self.combox_red.currentIndexChanged.connect(partial(
            self._set_symbol_band, 'red'))
        self.combox_green.currentIndexChanged.connect(partial(
            self._set_symbol_band, 'green'))
        self.combox_blue.currentIndexChanged.connect(partial(
            self._set_symbol_band, 'blue'))

        self.edit_redmin.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_redmin, 'red', 'min'))
        self.edit_redmax.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_redmax, 'red', 'max'))
        self.edit_greenmin.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_greenmin, 'green', 'min'))
        self.edit_greenmax.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_greenmax, 'green', 'max'))
        self.edit_bluemin.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_bluemin, 'blue', 'min'))
        self.edit_bluemax.editingFinished.connect(partial(
            self._set_symbol_minmax, self.edit_bluemax, 'blue', 'max'))

    def update_minmax_text(self):
        red = settings.symbol[self.index]['band_red']
        grn = settings.symbol[self.index]['band_green']
        blu = settings.symbol[self.index]['band_blue']

        self.edit_redmin.setText(str(settings.symbol[self.index]['min'][red]))
        self.edit_redmax.setText(str(settings.symbol[self.index]['max'][red]))

        self.edit_greenmin.setText(
            str(settings.symbol[self.index]['min'][grn]))
        self.edit_greenmax.setText(
            str(settings.symbol[self.index]['max'][grn]))

        self.edit_bluemin.setText(str(settings.symbol[self.index]['min'][blu]))
        self.edit_bluemax.setText(str(settings.symbol[self.index]['max'][blu]))

    def disconnect(self):
        self.combox_red.disconnect()
        self.combox_green.disconnect()
        self.combox_blue.disconnect()

        self.edit_redmin.disconnect()
        self.edit_redmax.disconnect()
        self.edit_greenmin.disconnect()
        self.edit_greenmax.disconnect()
        self.edit_bluemin.disconnect()
        self.edit_bluemax.disconnect()

    @QtCore.pyqtSlot()
    def _set_symbol_band(self, color, index):
        if color == 'red':
            settings.symbol[self.index]['band_red'] = index
        elif color == 'green':
            settings.symbol[self.index]['band_green'] = index
        elif color == 'blue':
            settings.symbol[self.index]['band_blue'] = index

        self.update_minmax_text()

    @QtCore.pyqtSlot()
    def _set_symbol_minmax(self, edit, color, minmax):
        if color == 'red':
            band = settings.symbol[self.index]['band_red']
        elif color == 'green':
            band = settings.symbol[self.index]['band_green']
        elif color == 'blue':
            band = settings.symbol[self.index]['band_blue']

        try:
            value = str2num(edit.text())
        except:
            edit.setText(str(settings.symbol[self.index][minmax][band]))
        else:
            settings.symbol[self.index][minmax][band] = value
            self.update_minmax_text()

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    widget = RasterSymbologyControl(None)

    widget.show()
    sys.exit(app.exec_())
