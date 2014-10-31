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
