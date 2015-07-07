""" Set up logger for TSTools and provide function for logging to QgsMessageBar
"""
import datetime as dt
import logging
import os

from qgis.gui import QgsMessageBar
import qgis.utils


class MsFormatter(logging.Formatter):
    """ Modified custom log handler by HappyLeapSecond for millisecond logging
    http://stackoverflow.com/questions/6290739/python-logging-use-milliseconds-in-time-format
    """
    converter = dt.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s

# Logging setup
_FORMAT = ('tstools:%(asctime)s:%(filename)s.%(funcName)s.%(levelname)s: '
           '%(message)s')
_formatter = MsFormatter(_FORMAT)
_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)

logger = logging.getLogger('tstools')
logger.handlers = []
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

if os.environ.get('TSTOOLS_DEBUG'):
    logger.setLevel(logging.DEBUG)


def qgis_log(msg, level=logging.INFO, duration=3):
    """ Log messages to GUI with message bar

    Note: Debug logging messages are not shown on the message bar

    Args:
      msg (str): message
      level (int, optional): logging module logging level
        (default: logging.INFO)
      duration (int): message duration on message bar

    """
    msgbar = True

    if level == logging.DEBUG:
        msgbar = False
    elif level == logging.INFO:
        qgis_level = QgsMessageBar.INFO
    elif level == logging.WARNING:
        qgis_level = QgsMessageBar.WARNING
    elif level in (logging.ERROR, logging.CRITICAL):
        qgis_level = QgsMessageBar.CRITICAL

    if msgbar:
        qgis.utils.iface.messageBar().pushMessage(
            logging.getLevelName(level),
            msg,
            level=qgis_level,
            duration=duration)
    logger.log(level, msg)
