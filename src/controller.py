# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCToolsDialog
                                 A QGIS plugin
 Plotting & visualization tools for CCDC Landsat time series analysis
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@bu.edu
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from functools import partial
import itertools

import numpy as np

from ccdc_timeseries import CCDCTimeSeries
import settings as setting

class Controller(object):

    def __init__(self, iface, control, ts_plot):
        """
        Controller stores options specified in control panel & makes them
        available for plotter by handling all signals...
        """
        self.iface = iface
        self.ctrl = control
        self.ts_plot = ts_plot

        self.configured = False

### Setup

    def get_time_series(self, location, image_pattern, stack_pattern):
        """
        Loads the time series class when called by ccdctools and feeds
        information to controls & plotter
        """
        try:
            self.ts = CCDCTimeSeries(location, image_pattern, stack_pattern)
        except:
            return False

        if self.ts:
            self.ctrl.init_plot_options(self.ts)
            self.ctrl.init_options()
            self.ctrl.init_symbology(self.ts)
            self.ctrl.update_table(self.ts)
            self.add_signals()
            self.configured = True
            return True

### Communications

    def update_display(self):
        """
        Once ts is read, update controls & plot with relevant information
        (i.e. update)
        """
        if setting.plot['auto_scale']:
            self.calculate_scale()
        self.ctrl.update_plot_options()
        self.ts_plot.update_plot(self.ts)

    def update_data(self):
        """
        Calls ts to refetch the dataset and then displays the update
        """
        self.ts.get_ts_pixel(self.ts.x, self.ts.y, setting.plot['fmask'])
        self.update_display()

### Common layer manipulation
    def add_map_layer(self, index):
        """
        Method called when adding an image via the table or plot.
        """
        print 'DEBUG %s : add_map_layer' % __file__
        reg = QgsMapLayerRegistry.instance()

        # Which layer are we adding?
        added = [(self.ts.stacks[index] == layer.source(), layer)
                 for layer in reg.mapLayers().values()]
        # Check if we haven't already added it
        if all(not add[0] for add in added) or len(added) == 0:
            # Create
            rlayer = QgsRasterLayer(self.ts.stacks[index],
                                    self.ts.image_ids[index])
            if rlayer.isValid():
                reg.addMapLayer(rlayer)
           # Add to settings "registry"
            setting.image_layers.append(rlayer)
            # Handle symbology
#            self.apply_symbology(rlayer)
        # If we have already added it, move it to top
        elif any(add[0] for add in added):
            print 'Have added layer, moving to top!'
            index = [i for i, tup in enumerate(added) if tup[0] == True][0]
#            self.move_layer_top(added[index][1].id())

    def map_layers_added(self, layers):
        """
        Check if newly added layer is part of stacks; if so, make sure image
        checkbox is clicked in the images tab. Also ensure
        setting.canvas['click_layer_id'] gets moved to the top
        """
        print 'Added a map layer'
        for layer in layers:
            rows_added = [row for (row, stack) in enumerate(self.ts.stacks)
                          if layer.source() == stack]
            print 'Added these rows: %s' % str(rows_added)
            for row in rows_added:
                item = self.ctrl.image_table.item(row, 0)
                if item:
                    if item.checkState() == Qt.Unchecked:
                        item.setCheckState(Qt.Checked)

        # Move pixel highlight back to top
        if setting.canvas['click_layer_id']:
            print 'Moving click layer back to top'
#            self.move_layer_top(setting.canvas['click_layer_id'])

    def map_layers_removed(self, layer_ids):
        """
        Unchecks image tab checkbox for layers removed and synchronizes
        image_layers in settings. Also ensures that
        setting.canvas['click_layer_id'] = None if the this layer is removed.
        
        Note that layers is a QStringList of layer IDs. A layer ID contains
        the layer name appended by the datetime added
        """
        print 'Removed a map layer'
        for layer_id in layer_ids:
            print layer_id

            # Remove from setting
            layer = QgsMapLayerRegistry.instance().mapLayers()[layer_id]
            if layer in setting.image_layers:
                setting.image_layers.remove(layer)
                print '    <----- removed a map layer from settting'

            # Find corresponding row in table
            rows_removed = [row for row, (image_id, fname) in
                enumerate(itertools.izip(self.ts.image_ids, self.ts.files))
                if image_id in layer_id or fname in layer_id]

            print 'Removed these rows %s' % str(rows_removed)

            # Uncheck if needed
            for row in rows_removed:
                item = self.ctrl.image_table.item(row, 0)
                if item:
                    if item.checkState() == Qt.Checked:
                        item.setCheckState(Qt.Unchecked)
            
            # Check for click layer
            if setting.canvas['click_layer_id'] == layer_id:
                print 'Removed click layer'
                print setting.canvas['click_layer_id']
                setting.canvas['click_layer_id'] = None

### Signals
    def add_signals(self):
        """
        Add the signals to the options tab
        """
        ### Options tab
        # Show/don't show where user clicked
        self.ctrl.cbox_showclick.stateChanged.connect(self.set_show_click)

        ### Plot tab
        # Catch signal from plot options that we need to update
        self.ctrl.plot_options_changed.connect(self.update_display)
        # Catch signal from Fmask plot option to fetch new data
        self.ctrl.refetch_data.connect(self.update_data)
        # Catch signal to save the figure
        self.ctrl.plot_save_request.connect(self.ts_plot.save_plot)
        # Add layer from time series plot points
        self.ctrl.cbox_plotlayer.stateChanged.connect(self.set_plotlayer)
        # Connect/disconnect matplotlib event signal based on checkbox default
        self.set_plotlayer(self.ctrl.cbox_plotlayer.checkState())

        ### Symbology tab
        # Signal for having applied symbology settings
        # self.ctrl.symbology_applied.connect(self.apply_symbology)

        ### Image tab panel helpers for add/remove layers
        # NOTE: QGIS added "layersAdded" in 1.8(?) to replace some older
        #       signals. It looks like they intended on adding layersRemoved
        #       to replace layersWillBeRemoved/etc, but haven't gotten around
        #       to it... so we keep with the old signal for now
        #       http://www.qgis.org/api/classQgsMapLayerRegistry.html
        QgsMapLayerRegistry.instance().layersAdded.connect(
            self.map_layers_added)
        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect(
            self.map_layers_removed)

        ### Image tab panel
        self.ctrl.image_table.itemClicked.connect(self.get_tablerow_clicked)


### Slots for signals

## Slots for map tool
    def fetch_data(self, pos):
        """
        Receives QgsPoint, transforms into pixel coordinates, retrieves data,
        and updates plot
        """
        print 'Pos {p}'.format(p=str(pos))
        # Convert position into pixel location
        px = int((pos[0] - self.ts.geo_transform[0]) /
                 self.ts.geo_transform[1] + 0.5)
        py = int((pos[1] - self.ts.geo_transform[3]) /
                 self.ts.geo_transform[5] + 0.5)

        print 'Pixel X/Y: {x}/{y}'.format(x=px, y=py)

        if px < self.ts.x_size and py < self.ts.y_size:
            # Fetch pixel values
            self.ts.get_ts_pixel(px, py, mask=setting.plot['fmask'])
            # Fetch CCDC fit
            self.ts.get_reccg_pixel(px, py)
            # Update plots
            self.ts_plot.update_plot(self.ts)

    def show_click(self, pos):
        """
        Receives QgsPoint and adds vector boundary of raster pixel clicked
        """
        print 'DEBUG: show click'

## Slots for options tab
    def set_show_click(self, state):
        """
        Updates showing/not showing of polygon where user clicked
        """
        if state == Qt.Checked:
            setting.canvas['show_click'] = True
        elif state == Qt.Unchecked:
            setting.canvas['show_click'] = False
            if setting.canvas['click_layer_id']:
                QgsMapLayerRegistry.instance().removeMapLayer(
                    setting.canvas['click_layer_id'])
                setting.canvas['click_layer_id'] = None

## Slots for time series table tab
    def get_tablerow_clicked(self, item):
        """
        If user clicks checkbox for image in image table, will add/remove
        image layer from map layers.
        """
        print '----------: get_tablerow_clicked'
        if item.column() != 0:
            return
        if item.checkState() == Qt.Checked:
            self.add_map_layer(item.row())
        elif item.checkState() == Qt.Unchecked:
            # If added is true and we now have unchecked, remove
            for layer in setting.image_layers:
                print layer
                print setting.image_layers
                if self.ts.stacks[item.row()] == layer.source():
                    QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

## Slots for plot window signals

    def set_plotlayer(self, state):
        """
        Turns on or off the adding of map layers for a data point on plot
        """
        if state == Qt.Checked:
            setting.plot['plot_layer'] = True
            self.cid = self.ts_plot.fig.canvas.mpl_connect('pick_event',
                                                       self.plot_add_layer)
        elif state == Qt.Unchecked:
            setting.plot['plot_layer'] = False
            self.ts_plot.fig.canvas.mpl_disconnect(self.cid)

    def plot_add_layer(self, event):
        """
        Receives matplotlib event and adds layer for data point picked
        
        Reference:
            http://matplotlib.org/users/event_handling.html
        """
        line = event.artist
        index = event.ind

        print 'Number selected: %s' % str(len(index))
        if len(index) > 1:
            print 'Error, selected more than one item...'
            print 'Defaulting to the first'
            index = index[0]

        print 'Selected date %s' % str(line.get_xdata()[index])

        self.add_map_layer(index)


    def calculate_scale(self):
        """
        Automatically calculate the min/max for time series plotting as the
        2nd and 98th percentile of each band's time series
        """
        print 'Calculating scaling'
        setting.plot['min'] = [np.percentile(np.ma.compressed(band), 2)
                                for band in self.ts.data[:, ]]
        setting.plot['max'] = [np.percentile(np.ma.compressed(band), 98)
                                for band in self.ts.data[:, ]]
#        setting.plot['min'] = [min(0, np.min(band) * 
#                                   (1 - setting.plot['scale_factor']))
#                           for band in self.ts.data[:, ]]
#        setting.plot['max'] = [max(10000, np.max(band) * 
#                                   (1 + setting.plot['scale_factor']))
#                           for band in self.ts.data[:, ]]

    def disconnect(self):
        """
        Disconnect all signals added to various components
        """
        if self.configured:
    #        self.ctrl.symbology_applied.disconnect()
                self.ctrl.image_table.itemClicked.disconnect()
                self.ctrl.cbox_showclick.stateChanged.disconnect()              
                self.ctrl.plot_options_changed.disconnect()
                self.ctrl.refetch_data.disconnect()
                self.ctrl.plot_save_request.disconnect()
                self.ctrl.cbox_plotlayer.stateChanged.disconnect()
    
