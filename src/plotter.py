""" Module to handle plot requests
"""
import logging

from PyQt4 import QtCore, QtGui
import qgis.utils

from .logger import qgis_log


@QtCore.pyqtSlot()
def plot_request(pos):
    """ Plot request for a given position

    """
    qgis_log('Clicked a point {p}'.format(p=pos), level=logging.INFO)
