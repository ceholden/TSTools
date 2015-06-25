""" Make plugin known to QGIS
"""


def classFactory(iface):
    # load TSTools class from file TSTools
    from .tstools import TSTools
    return TSTools(iface)
