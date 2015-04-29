# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
"""
/***************************************************************************
 Timeseries manager
                                 A QGIS plugin
 Plugin for visualization and analysis of remote sensing time series
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@gmail.com
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
import importlib
import logging
import os
import pkgutil

logger = logging.getLogger('tstools')


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

        file_location = os.path.dirname(__file__)
        self.plugin_dir.append('./' if file_location == '' else file_location)

        self.find_timeseries()

    def find_timeseries(self):
        """ Try to find timeseries classes """
        try:
            from tstools.ts_driver import timeseries
        except ImportError:
            logger.warning('Could not import "timeseries". Check your path')
            raise
        else:
            logger.debug('Found "timeseries" module')

        # Use pkgutil to search for timeseries
        logger.debug('Module name: {n}'.format(n=__name__))
        for loader, modname, ispkg in pkgutil.iter_modules(self.plugin_dir):
            if modname != __name__.split('.')[-1]:
                logger.debug('Loading {m}'.format(m=modname))

                importlib.import_module('.'.join(__name__.split('.')[:-1]) +
                                        '.' + modname)

        self.ts_drivers = timeseries.AbstractTimeSeries.__subclasses__()
        for tsd in self.ts_drivers:
            logger.info('Found driver: {tsd}'.format(tsd=tsd))

        # Find even more descendents
        for subclass in self.ts_drivers:
            self.recursive_find_subclass(subclass)

    def recursive_find_subclass(self, subclass):
        """ Search subclass for descendents """

        sub_subclasses = subclass.__subclasses__()

        for sub_subclass in sub_subclasses:
            if sub_subclass not in self.ts_drivers:
                self.ts_drivers.append(sub_subclass)
                logger.debug('Found driver: {tsd}'.format(tsd=sub_subclass))
            self.recursive_find_subclass(sub_subclass)


# Store timeseries manager
tsm = TSManager()
logger.info(tsm.ts_drivers)
