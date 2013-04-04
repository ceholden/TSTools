# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CCDCTools
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
 This script initializes the plugin, making it known to QGIS.
"""


def name():
    return "CCDCTools"


def description():
    return "Plotting & visualization tools for CCDC Landsat time series analysis"


def version():
    return "Version 0.6"


def icon():
    return "icon.png"


def qgisMinimumVersion():
    return "1.8"

def author():
    return "Chris Holden"

def email():
    return "ceholden@bu.edu"

def classFactory(iface):
    # load CCDCTools class from file CCDCTools
    from ccdctools import CCDCTools
    return CCDCTools(iface)
