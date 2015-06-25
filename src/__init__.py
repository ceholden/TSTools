""" TSTools QGIS Plugin: __init__.py
"""


def classFactory(iface):
    # load TSTools class from file TSTools
    from .tstools import TSTools
    return TSTools(iface)
