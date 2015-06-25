""" Create configuration dialog for initializing timeseries drivers.
"""
from collections import OrderedDict
import logging

from PyQt4 import QtCore, QtGui

from ui_config import Ui_Config

from . import settings
from .ts_driver.ts_manager import tsm
from .utils.custom_form import CustomForm

logger = logging.getLogger('tstools')


class Config(QtGui.QDialog, Ui_Config):

    accepted = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)

        # Setup required information
        self.location = settings.location
        self.data_model_str = [_ts.description for _ts in tsm.ts_drivers]
        self.custom_options = None

        # Finish setup
        self.setup_config()

    def setup_config(self):
        # Data model types
        self.combox_ts_model.clear()
        self.combox_ts_model.addItems(self.data_model_str)

        self.combox_ts_model.activated.connect(self.ts_model_changed)

        # Setup location text field and open button
        self.edit_location.setText(self.location)
        self.button_location.clicked.connect(self.select_location)

        # Setup stacked widget for custom options
        self.stacked_widget = QtGui.QStackedWidget()

        self.custom_forms = []
        for i, _ts in enumerate(tsm.ts_drivers):
            # Test for custom configurations

            has_custom_form = True

            if not hasattr(_ts, 'config') or not hasattr(_ts, 'config_names'):
                has_custom_form = False
            else:
                if not isinstance(_ts.config, list) or not _ts.config:
                    logger.error(
                        'Custom options for timeseries {ts} improperly '
                        'described'.format(ts=_ts))
                    has_custom_form = False

            if has_custom_form is True:
                # Create OrderedDict for CustomForm
                default_config = OrderedDict([
                    [key, [name, getattr(_ts, key)]] for key, name in
                    zip(_ts.config, _ts.config_names)
                ])

                custom_form = CustomForm(default_config)
                self.custom_forms.append(custom_form)
            else:
                custom_form = QtGui.QLabel('No custom config options')
                self.custom_forms.append(None)

            custom_form.setParent(self.stacked_widget)
            self.stacked_widget.insertWidget(i, custom_form)

        self.custom_layout = QtGui.QVBoxLayout()
        self.custom_layout.addWidget(self.stacked_widget)
        self.custom_widget.setLayout(self.custom_layout)

        # Setup dialog buttons
        # Init buttons
        self.ok = self.button_box.button(QtGui.QDialogButtonBox.Ok)
        self.cancel = self.button_box.button(QtGui.QDialogButtonBox.Cancel)
        # Add signals
        self.ok.pressed.connect(self.accept_config)
        self.cancel.pressed.connect(self.cancel_config)

    @QtCore.pyqtSlot(int)
    def ts_model_changed(self, index):
        """ Fired when combo box is changed so stacked_widget can change """
        if index != self.stacked_widget.currentIndex():
            self.stacked_widget.setCurrentIndex(index)
            self.combox_ts_model.setCurrentIndex(index)

    @QtCore.pyqtSlot()
    def select_location(self):
        """
        Brings up a QFileDialog allowing user to select a folder
        """
        self.location = QtGui.QFileDialog.getExistingDirectory(
            self,
            'Select stack location',
            self.location,
            QtGui.QFileDialog.ShowDirsOnly)
        self.edit_location.setText(self.location)

    @QtCore.pyqtSlot()
    def accept_config(self):
        print 'Okay pressed!'
        self.location = str(self.edit_location.text())

        self.model_index = self.combox_ts_model.currentIndex()

        if self.custom_forms[self.model_index] is not None:
            self.custom_options = self.custom_forms[self.model_index].get()
        else:
            self.custom_options = None

        self.accepted.emit()

    @QtCore.pyqtSlot()
    def cancel_config(self):
        logger.info('Cancel pressed!')
        self.canceled.emit()
