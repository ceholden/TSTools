import numpy as np

from .. import settings


def ravel_series_band(i_series, i_band):
    """ Returns the 1D index for i'th series and i'th band """
    idx = np.where((settings.plot_series == i_series) &
                   (settings.plot_band_indices == i_band))[0]
    if idx.size == 0:
        raise IndexError('Unable to unravel provided series and band indices'
                         ' ({s} and {b})'.format(s=i_series, b=i_band))
    else:
        return idx[0]
