""" Various utilities useful for timeseries drivers
"""
import fnmatch
import logging
import os

import numpy as np

try:
    from scandir import walk
except ImportError:
    from os import walk

logger = logging.getLogger('tstools')


def check_cache(cache_folder):
    """ Checks location for ability to read/write from cache

    Args:
      cache_folder (str): location of cache folder

    Returns:
      (read_cache, write_cache): tuple of booleans describing ability to read
        and write from cache

    """
    read_cache = False
    write_cache = False

    if os.path.isdir(cache_folder):
        if os.access(cache_folder, os.R_OK):
            read_cache = True

        if os.access(cache_folder, os.W_OK):
            write_cache = True
    else:
        try:
            os.mkdirs(cache_folder)
        except:
            pass
        else:
            read_cache = True
            write_cache = True

    return (read_cache, write_cache)


def name_cache_pixel(x, y, shape, prefix='', suffix=''):
    """ Return a filename for a pixel cache file

    Args:
      x (int): column of pixel
      y (int): row of pixel
      shape (tuple): shape of Y data to save
      prefix (str, optional): prefix to pixel cache filename
      suffix (str, optional): suffix to pixel cache filename

    Returns:
      str: cache filename

    """
    f = 'x%s_y%s_n%s_b%s' % (x, y, shape[1], shape[0])

    return prefix + f + suffix + '.npz'


def write_cache_pixel(filename, series):
    """ Save one series data to NumPy zipped array

    Args:
      filename (str): filename of cache file
      series (Series): Series within timeseries driver to save

    Raises:
      IOError: raise IOError if it cannot write to cache

    """
    logger.debug('Caching pixel to %s' % filename)
    np.savez(filename,
             **{'Y': series.data,
                'image_IDs': series.images['id']})


def read_cache_pixel(filename, series):
    """ Returns data read in from cache file if passes validation

    Args:
      filename (str): filename of cache file
      series (Series): Series within timeseries driver to read

    Returns:
      np.ndarray: 2D np.ndarray of 'Y' data for series

    Raises:
      IOError: raise IOError if cache file cannot correctly be read from disk
      IndexError: raise IndexError if cached data does not match dimensions
        or images used in timeseries series

    """
    z = np.load(filename)
    if 'Y' not in z.files or 'image_IDs' not in z.files:
        raise IndexError('Cache file is not in the correct format')

    if np.array_equal(z['image_IDs'], series.images['id']):
        return z['Y']
    else:
        raise IndexError('Could not find cache data for series %s. image_IDs '
                         'are not the same' % series.description)


def name_cache_line(y, shape, prefix='', suffix=''):
    """ Return a filename for a line cache file

    Args:
      y (int): row of pixel
      shape (tuple): shape of Y data to save
      prefix (str, optional): prefix to pixel cache filename
      suffix (str, optional): suffix to pixel cache filename

    Returns:
      str: cache filename

    """
    f = 'r%s_n%s_b%s' % (y, shape[1], shape[0])

    return prefix + f + suffix + '.npz'


def read_cache_line(filename, series):
    """ Returns data read in from cache file if passes validation

    Args:
      filename (str): filename of cache file
      series (Series): Series within timeseries driver to read

    Returns:
      np.ndarray: 3D np.ndarray of 'Y' data for series

    Raises:
      IOError: raise IOError if cache file cannot correctly be read from disk
      IndexError: raise IndexError if cached data does not match dimensions
        or images used in timeseries series

    """
    z = np.load(filename)
    if 'Y' not in z.files or 'image_IDs' not in z.files:
        raise IndexError('Cache file is not in the correct format')

    if np.array_equal(z['image_IDs'], series.images['id']):
        return z['Y']
    else:
        raise IndexError('Could not find cache data for series %s. image_IDs '
                         'are not the same' % series.description)


def find_files(location, pattern, ignore_dirs=[], maxdepth=float('inf')):
    """ Find paths to images on disk matching an given pattern

    Args:
      location (str): root directory to search
      pattern (str): glob style pattern to search for
      ignore_dirs (iterable): list of directories to ignore from search
      maxdepth (int): maximum depth to recursively search

    Returns:
      list: list of files within location matching pattern

    """
    results = []

    if isinstance(ignore_dirs, str):
        ignore_dirs = list(ignore_dirs)

    location = os.path.normpath(location)
    num_sep = location.count(os.path.sep) - 1

    for root, dirs, files in walk(location, followlinks=True):
        if ignore_dirs:
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

        depth = root.count(os.path.sep) - num_sep
        if depth > maxdepth:
            dirs[:] = []
            files[:] = []

        for fname in fnmatch.filter(files, pattern):
            results.append(os.path.abspath(os.path.join(root, fname)))

    return results


def set_custom_config(obj, values):
    """ Set custom configuration options

    Args:
      obj (object): object to set values
      values (iterable): new values to set to variables defined in `obj.config`

    Raises:
      AttributeError: raise AttributeError if `obj` doesn't have a `config` or
        if `values` passed are not same type as current values in `obj` for a
        given attribute in `config`

    """
    if not hasattr(obj, 'config'):
        raise AttributeError('Cannot set custom config for object without'
                             ' config attribute')

    for val, attr in zip(values, obj.config):
        current_val = getattr(obj, attr, None)

        _msg = '    {a} : {cv} <-- {v} ({t})'.format(a=attr,
                                                     v=val,
                                                     cv=current_val,
                                                     t=type(val))
        logger.debug(_msg)

        if isinstance(val, type(current_val)):
            setattr(obj, attr, val)
        else:
            raise AttributeError(
                'Cannot set value {v} for {o} (current value {cv}) '
                'because types do not match ({t1} vs. {t2})'
                .format(v=val, o=attr, cv=current_val,
                        t1=type(val), t2=type(current_val)))


def parse_landsat_MTL(mtl_file, key):
    """ Returns the value of specified key for a given Landsat MTL file

    Args:
        mtl_file (str): filename of MTL file
        key (str or list of str): metadata key(s) to search for

    Returns:
        dict: integer representation of value if possible, else a string, of
            the value for each input key

    """
    if isinstance(key, str):
        key = [key]
    out = {}
    with open(mtl_file, 'rb') as f:
        for line in f:
            for _key in key:
                if _key in line:
                    value = line.strip().split('=')[1].strip().strip('"')
                    try:
                        value = int(value)
                    except:
                        pass
                    out[_key] = value
    return out
