""" Module that stores current settings used in TSTools plugin
"""
import os

import numpy as np


# General settings
location = os.getcwd()
map_tool = True

# List of raster images added - used to track for symbology
image_layers = []

# Dictionary to store plot settings
plot = {
    # Should we plot when we click canvas?
    'plot_layer': True,
    # Which band to plot
    'band': 0,
    # Plot scaling options
    'auto_scale': True,
    'yscale_all': False,
    'xscale_fix': False,
    'xscale_range': None,
    'scale_factor': 0.25,
    # Plot min, max
    'min': np.zeros(1, dtype=np.int),
    'max': np.ones(1, dtype=np.int) * 10000,
    'xmin': None,
    'xmax': None,
    # Show Fmask, CCDC fit, time series breaks
    'mask': True,
    'fit': True,
    'break': True,
    # Fmask values
    'mask_val': None,
    # Tolerance for clicking data points
    'picker_tol': 2
}

# Dictionary to store plot symbology options
plot_symbol = {
    'enabled': False,
    'indices': None,
    'markers': None,
    'colors': None
}

save_plot = {

    'fname': 'time_series_plot',
    'format': 'png',
    'transparent': False,
    'facecolor': 'w',
    'edgecolor': 'w'

}

# Dictionary to store raster symbology settings
p_symbol = {
    # Pre-apply options
    # Control symbology?
    'control': True,
    # RGB color options
    'band_red': 4,
    'band_green': 3,
    'band_blue': 2,
    # Min/max values for all bands
    'min': np.zeros(1, dtype=np.int),
    'max': np.ones(1, dtype=np.int) * 10000,
    # Contrast enhancement
    #   NoEnhancement                           0
    #   StretchToMinimumMaximum                 1
    #   StretchAndClipToMinimumMaximum          2
    #   ClipToMinimumMaximum                    3
    'contrast': 1,
}
symbol = {
    # Control symbology?
    'control': True,

    # Post-apply options
    'band_red': 4,
    'band_green': 3,
    'band_blue': 2,
    'min': np.zeros(1, dtype=np.int),
    'max': np.ones(1, dtype=np.int) * 10000,
    'contrast': 1,
}

canvas = {
    # Show outline of clicked pixel
    'show_click': True,
    # QgsVectorLayer ID for polygon outline of clicked pixel
    'click_layer_id': None
}
