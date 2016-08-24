""" Find, detect, and make available timeseries drivers implementations

Timeseries drivers must be enumerated in tstools.ts_drivers.drivers.DRIVERS
or be a part of the TSTools.drivers entry point to be detected.
"""
import importlib
from pkg_resources import iter_entry_points
import sys

from .drivers import DRIVERS
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
        self.description = 'Broken: %s' % module


class TSManager(object):
    """ Timeseries Manager

    Finds and stores references to available timeseries
    """
    # Loaded timeseries
    ts = None

    def __init__(self, location=None):
        # All available timeseries
        self.ts_drivers = []
        self.find_timeseries()

    def find_timeseries(self):
        """ Try to find timeseries classes """
        broken = []

        for name, import_path in DRIVERS.items():
            try:
                driver = getattr(importlib.import_module(import_path), name)
                self.ts_drivers.append(driver)
            except ImportError as exc:
                logger.error('Cannot import %s: %s' % (name, exc))
                broken_module = BrokenModule(name, exc)
                broken.append(broken_module)
            except:
                logger.error('Cannot import %s: %s' %
                             (name, sys.exc_info()[0]))

        for plugin in iter_entry_points('TSTools.drivers'):
            try:
                driver = plugin.load()
                self.ts_drivers.append(driver)
            except ImportError as exc:
                logger.error('Cannot import %s: %s' % (plugin.name, exc))
                broken_module = BrokenModule(plugin.name, exc)
                broken.append(broken_module)
            except:
                logger.error('Cannot import %s: %s' %
                             (plugin.name, sys.exc_info()[0]))
                raise

        for tsd in self.ts_drivers:
            logger.info('Found driver: {tsd}'.format(tsd=tsd))

        self.ts_drivers.extend(broken)


# Store timeseries manager
tsm = TSManager()
logger.debug('Found {i} TS data models'.format(i=len(tsm.ts_drivers)))
