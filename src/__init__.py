# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TSTools
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-10-01
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
 This script initializes the plugin, making it known to QGIS.
"""

import logging

FORMAT = '%(filename)s.%(funcName)s - %(levelname)s: %(message)s'
formatter = logging.Formatter(FORMAT)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger('tstools')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def name():
    return "TSTools"


def description():
    return "Plugin for visualization and analysis \
            of remote sensing time series"


def version():
    return "Version 0.1"


def icon():
    return "icon.png"


def qgisMinimumVersion():
    return "2.0"


def author():
    return "Chris Holden"


def email():
    return "ceholden@gmail.com"


def classFactory(iface):
    # load TSTools class from file TSTools
    from .tstools import TSTools
    return TSTools(iface)
