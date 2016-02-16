""" Data store for current settings used in TSTools plugin
"""
import datetime as dt
import os

import numpy as np


# General settings
location = os.getcwd()
map_tool = True

# List of raster images added - used to track for symbology
image_layers = []

# Series index for symbology and images table
series_index_symbology = 0
series_index_table = 0

# Series to plot options "band" QComboBox
plot_series = []
plot_band_indices = []
plot_bands = []

# Dictionary to store plot settings
plot_current = 0
plot_dirty = []
plot = {
    # Style
    # 'style': 'xkcd' if ('bu.edu' in os.uname()[1] and
    #                     dt.date.today().weekday() >= 5) else 'ggplot',
    'style': os.environ.get('TSTOOLS_PLOT_STYLE', 'ggplot'),
    # Should we plot when we click canvas?
    'plot_layer': True,
    # Axis selector for controls
    'axis_select': 0,
    # Which band to plot on which axes
    'y_axis_1_band': np.zeros(1, dtype=np.bool),
    'y_axis_2_band': np.zeros(1, dtype=np.bool),
    # Plot scaling options
    'y_axis_scale_auto': [True, True],
    'x_scale_fix': False,
    'x_scale_range': None,
    'scale_factor': 0.25,
    # Plot min, max
    'y_min': [0, 0],
    'y_max': [10000, 10000],
    'x_min': dt.date.today().year,
    'x_max': dt.date.today().year + 1,
    # Show mask, model fit, time series breaks
    'mask': True,
    'fit': True,
    'break': True,
    # Mask values
    'mask_val': None,
    # Allow custom text/lines/etc from timeseries driver
    'custom': True,
    # Tolerance for clicking data points
    'picker_tol': 2
}

# Dictionary to store plot symbology options
plot_symbol = []  #  all bands from all series added together
default_plot_symbol = {
    'enabled': False,  # bool
    'indices': None,  # list of np.array
    'markers': 'o',  # list of str
    'colors': [0, 0, 150]  # list of tuple of 0-255 e.g., (0, 255, 0)
}

save_plot = {
    'fname': 'time_series_plot',
    'format': 'png',
    'transparent': False,
    'facecolor': 'w',
    'edgecolor': 'w'
}

# Enable/disable symbology control for all Series
symbol_control = True
# Dictionary to store raster symbology settings
symbol = []
# Defaults for `symbol`
default_symbol = {
    'type': 'RGB',
    # RGB color options
    'band_red': 5,
    'band_green': 4,
    'band_blue': 3,
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

canvas = {
    # Show outline of clicked pixel
    'show_click': True,
    # QgsVectorLayer ID for polygon outline of clicked pixel
    'click_layer_id': None
}

#: configuration options for saving using ``np.savetxt``
savetxt = {
    'fmt': '%10.5f',
    'delimiter': ','
}
