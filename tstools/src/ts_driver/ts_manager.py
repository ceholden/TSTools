""" Find, detect, and make available timeseries drivers implementations

Timeseries drivers must inherit from the Abstract Base Class
"AbstractTimeSeriesDriver" to be detected.
"""
import importlib
import os
import pkgutil
import sys

from ..logger import logger


class BrokenModule(object):
    """ Timeseries driver module "%s" is broken.

    Reason:
    %s

    Please see TSTools Github repository for more information or to report an
    issue:

    <a href="https://github.com/ceholden/TSTools">TSTools</a>
    """
    def __init__(self, module, message):
        self.__doc__ = self.__doc__ % (module, message)


class TSManager(object):
    """ Timeseries Manager

    Finds and stores references to available timeseries
    """
    # Loaded timeseries
    ts = None

    def __init__(self, location=None):
        # Location of timeseires modules
        self.plugin_dir = []
        # All available timeseries
        self.ts_drivers = []

        if location and os.path.isdir(location):
            self.plugin_dir.append(location)

        file_location = os.path.join(os.path.dirname(__file__), 'drivers')
        self.plugin_dir.append('./' if file_location == '' else file_location)

        self.find_timeseries()

    def find_timeseries(self):
        """ Try to find timeseries classes """
        try:
            from . import timeseries
        except ImportError:
            logger.critical('Could not import "timeseries". Check your path')
            raise
        else:
            logger.debug('Found "timeseries" module')

        broken = []

        # Use pkgutil to search for timeseries
        logger.debug('Module name: {n}'.format(n=__name__))
        for loader, modname, ispkg in pkgutil.walk_packages(self.plugin_dir):
            full_path = '%s.drivers.%s' % (__name__.rsplit('.', 1)[0], modname)
            try:
                importlib.import_module(full_path)
            except ImportError as e:
                logger.error('Cannot import %s: %s' % (modname, e.message))
                broken_module = BrokenModule(modname,
                                             e.args[0] if e.args else
                                             'Unknown import error')
                broken_module.description = 'Broken: %s' % modname
                broken.append(broken_module)
            except:
                logger.error('Cannot import %s: %s' %
                             (modname, sys.exc_info()[0]))
                raise

        self.ts_drivers = timeseries.AbstractTimeSeriesDriver.__subclasses__()
        for tsd in self.ts_drivers:
            logger.info('Found driver: {tsd}'.format(tsd=tsd))

        # Find even more descendents
        for subclass in self.ts_drivers:
            self.recursive_find_subclass(subclass)

        self.ts_drivers.extend(broken)

    def recursive_find_subclass(self, subclass):
        """ Search subclass for descendents """

        sub_subclasses = subclass.__subclasses__()

        for sub_subclass in sub_subclasses:
            if sub_subclass not in self.ts_drivers:
                self.ts_drivers.append(sub_subclass)
                logger.info('Found driver: {tsd}'.format(tsd=sub_subclass))
            self.recursive_find_subclass(sub_subclass)


# Store timeseries manager
tsm = TSManager()
logger.debug('Found {i} TS data models'.format(i=len(tsm.ts_drivers)))
