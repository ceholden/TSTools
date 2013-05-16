# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 ccdc_settings
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
"""

import numpy as np

# Dictionary to store plot settings
plot = {
    # Which band to plot
    'band'          :       0,
    # Plot scaling options
    'auto_scale'    :       True,
    'scale_factor'  :       0.25,
    # Plot min, max
    'min'           :       np.zeros(1, dtype=np.int),
    'max'           :       np.zeros(1, dtype=np.int) * 10000,
    # Show Fmask, CCDC fit, time series breaks
    'fmask'         :       True,
    'fit'           :       True,
    'break'         :       True,
    # Tolerance for clicking data points
    'picker_tol'    :       2
}


