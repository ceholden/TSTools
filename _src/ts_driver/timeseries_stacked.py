import logging

import timeseries

logger = logging.getLogger('tstools')


class LayerStackTimeSeries(timeseries.AbstractTimeSeries):

    description = 'Layer Stacked Time Series'

    # Dataset attributes
    image_names = []
    filenames = []
    filepaths = []
    dates = []
    length = 0
    n_band = 0

    # Dataset geographic attributes
    x_size = 0
    y_size = 0
    geo_transform = []
    projection = None

    # Result attributes
    has_results = False
    result = []

    # Caching attributes
    read_cache = False
    write_cache = False

    # Configuration attributes
    image_pattern = ''
    stack_pattern = ''
    results_folder = ''
    results_pattern = ''
    cache_folder = 'cache'
    mask_band = 8
    days_in_year = 365.25

    configurable = ['image_pattern', 'stack_pattern',
                    'results_folder', 'results_pattern',
                    'cache_folder', 'mask_band',
                    'days_in_year']
    configurable_str = ['Image folder pattern', 'Stack Pattern',
                        'Results folder', 'Results pattern',
                        'Cache folder pattern', 'Mask band',
                        'Days in Year']


    def __init__(self):
        pass
