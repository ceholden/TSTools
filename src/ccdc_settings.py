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

# List of raster images added - used to track for symbology
image_layers = []

# Dictionary to store plot settings
plot = {
    # Should we plot when we click canvas?
    'plot_layer'    :       True,
    # Which band to plot
    'band'          :       0,
    # Plot scaling options
    'auto_scale'    :       True,
    'scale_factor'  :       0.25,
    # Plot min, max
    'min'           :       np.zeros(1, dtype=np.int),
    'max'           :       np.ones(1, dtype=np.int) * 10000,
    # Show Fmask, CCDC fit, time series breaks
    'fmask'         :       True,
    'fit'           :       True,
    'break'         :       True,
    # Fmask values
    'mask_val'      :       [2, 3, 4, 255],
    # Tolerance for clicking data points
    'picker_tol'    :       2
}

save_plot = {

    'fname'         :       'time_series_plot',
    'format'        :       'png',
    'transparent'   :       False,
    'facecolor'     :       'w',
    'edgecolor'     :       'w'

}

# Dictionary to store raster symbology settings
p_symbol = {
    ### Pre-apply options
    # Control symbology?
    'control'       :       True,
    # RGB color options
    'band_red'      :       4,
    'band_green'    :       3,
    'band_blue'     :       2,
    # Min/max values for all bands
    'min'           :       np.zeros(1, dtype=np.int),
    'max'           :       np.ones(1, dtype=np.int) * 10000,
    # Contrast enhancement
    #   NoEnhancement                           0
    #   StretchToMinimumMaximum                 1
    #   StretchAndClipToMinimumMaximum          2
    #   ClipToMinimumMaximum                    3
    'contrast'      :       1,
}
symbol = {
    # Control symbology?
    'control'       :       True,

    ### Post-apply options
    'band_red'      :       4,
    'band_green'    :       3,
    'band_blue'     :       2,
    'min'           :       np.zeros(1, dtype=np.int),
    'max'           :       np.ones(1, dtype=np.int) * 10000,
    'contrast'      :       1,
}

canvas = {
    # Show outline of clicked pixel
    'show_click'        :       True,
    # QgsVectorLayer ID for polygon outline of clicked pixel
    'click_layer_id'    :       None
}
