import fnmatch
import logging
import os

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

    for root, dirs, files in os.walk(location, followlinks=True):
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
      key (str): metadata key to search for

    Returns:
      str or int: returns integer representation of value if possible, else
        as a string

    """
    with open(mtl_file, 'rb') as f:
        for line in f:
            if key in line:
                value = line.strip().split('=')[1].strip()
                try:
                    value = int(value)
                    return value
                except:
                    return value
