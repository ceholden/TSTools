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
#from qgis.core import QgsFeature, QgsGeometry, QgsRasterLayer, QgsMapLayerRegistry
from qgis.core import *

from functools import partial
import itertools

import numpy as np

from ccdc_timeseries import CCDCTimeSeries, CCDCLengthError
import ccdc_settings as setting

class Controller(object):

    def __init__(self, control, plot, iface):
        """
        Controller stores options specified in control panel & makes them
        available for plotter by handling all signals...
        """
        self.ctrl = control
        self.plt = plot
        self.iface = iface

    def get_time_series(self, location, image_pattern, stack_pattern):
        """
        Loads the time series class when called by ccdctools and feeds
        information to controls & plotter
        """
        try:
            self.ts = CCDCTimeSeries(location, image_pattern, stack_pattern)
        except:
            print 'Length error'
            return False

        if self.ts:
            # Init symbology, table & signals
            self.ctrl.init_plot_options(self.ts)
            self.ctrl.init_symbology(self.ts)
            self.ctrl.update_table(self.ts)
            self.plt.update_plot(self.ts)
            self.add_signals()
            return True

    def update_display(self):
        """
        Once ts is read, update controls & plot with relevant information
        (i.e. update)
        """
        if setting.plot['auto_scale']:
            self.calculate_scale()
        self.ctrl.update_plot_options()
        self.plt.update_plot(self.ts)

    def add_signals(self):
        """
        Add the signals to the options tab
        """
        ### Plot tab
        # Catch signal from plot options that we need to update
        self.ctrl.plot_options_changed.connect(self.update_display)
        # Show/don't show where user clicked
        self.ctrl.cbox_showclick.stateChanged.connect(self.set_show_click)
        # Add layer from time series plot points
        self.ctrl.cbox_plotlayer.stateChanged.connect(self.set_plotlayer)
        # Connect/disconnect matplotlib event signal based on checkbox default
        self.set_plotlayer(self.ctrl.cbox_plotlayer.checkState())

        ### Symbology tab
        # Signal for having applied symbology settings
        self.ctrl.symbology_applied.connect(self.apply_symbology)

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
        # Image tab panel
        self.ctrl.image_table.itemClicked.connect(self.get_tablerow_clicked)

    def apply_symbology(self, rlayers=None):
        """
        Apply time series symbology to a raster layer or all layers added from
        time series
        """
        print 'Applying symbology!!!!'
        
        if rlayers is None:
            rlayers = setting.image_layers
        elif type(rlayers) != type([]):
            rlayers = [rlayers]

        # Fetch band indexes
        red_band = setting.symbol['band_red'] 
        green_band = setting.symbol['band_green']
        blue_band = setting.symbol['band_blue']
        
        for rlayer in rlayers:
            # Force RGB color image
            rlayer.setDrawingStyle(QgsRasterLayer.MultiBandColor)
            # Setup raster band to color pairing
            rlayer.setRedBandName(rlayer.bandName(red_band + 1))
            rlayer.setGreenBandName(rlayer.bandName(green_band + 1))
            rlayer.setBlueBandName(rlayer.bandName(blue_band + 1))
            # Setup min/max
            rlayer.setMinimumValue(red_band + 1, 
                                   setting.symbol['min'][red_band], False)
            rlayer.setMinimumValue(green_band + 1,  
                                   setting.symbol['min'][green_band], False)
            rlayer.setMinimumValue(blue_band + 1,  
                                   setting.symbol['min'][blue_band], False)
            rlayer.setMaximumValue(red_band + 1,  
                                   setting.symbol['max'][red_band], False)
            rlayer.setMaximumValue(green_band + 1,
                                   setting.symbol['max'][green_band], False)
            rlayer.setMaximumValue(blue_band + 1,
                                   setting.symbol['max'][blue_band], False)
            rlayer.setUserDefinedRGBMinimumMaximum(True)
            # Contrast
            rlayer.setContrastEnhancementAlgorithm(setting.symbol['contrast'])
            # Refresh & update symbology in legend
            if hasattr(rlayer, 'setCacheImage'):
                rlayer.setCacheImage(None)
            rlayer.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(rlayer)

    def calculate_scale(self):
        """
        Automatically calculate the min/max for time series plotting
        """
        setting.plot['min'] = [np.min(band) * (1 - setting.plot['scale_factor'])
                           for band in self.ts.data[:, ]]
        setting.plot['max'] = [np.max(band) * (1 + setting.plot['scale_factor'])
                           for band in self.ts.data[:, ]]

    ### Slots for options tab
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

    def set_plotlayer(self, state):
        """
        Turns on or off the adding of map layers for a data point on plot
        """
        if state == Qt.Checked:
            setting.plot['plot_layer'] = True
            self.cid = self.plt.fig.canvas.mpl_connect('pick_event',
                                                       self.plot_add_layer)
        elif state == Qt.Unchecked:
            setting.plot['plot_layer'] = False
            self.plt.fig.canvas.mpl_disconnect(self.cid)

    ### Slots for plot window
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

    ### Function helper for MapTool slot
    def fetch_data(self, pos):
        """
        Receives QgsPoint, transforms into pixel coordinates, retrieves data
        and updates plot
        """
        print 'Pos: %s' % str(pos)
        px = int((pos[0] - self.ts.geo_transform[0]) / 
                 self.ts.geo_transform[1])
        py = int((pos[1] - self.ts.geo_transform[3]) / 
                 self.ts.geo_transform[5])
        print 'Pixel x/y %s/%s' % (px, py)

        if px <= self.ts.x_size and py <= self.ts.y_size:
            self.ts.get_ts_pixel(px, py, mask=setting.plot['fmask'])
            self.ts.get_reccg_pixel(px, py)
            print 'nBreaks = %s' % len(self.ts.reccg)
            self.plt.update_plot(self.ts)

    def show_click(self, pos):
        """
        Receives QgsPoint and adds shapefile boundary of raster pixel clicked
        """
        print 'Showing where user clicked...!'
        reg = QgsMapLayerRegistry.instance()
        ### First store last layer selected
        last_selected = self.iface.activeLayer()
        ### Getting raster x, y
        GT = self.ts.geo_transform
        px = int((pos[0] - GT[0]) /
                 GT[1])
        py = int((pos[1] - GT[3]) /
                 GT[5])
        # Upper left coordinates
        ulx = (GT[0] + px * GT[1] + py * GT[2])
        uly = (GT[3] + px * GT[4] + py * GT[5])
        ### Create geometry
        gSquare = QgsGeometry.fromPolygon( [[ 
            QgsPoint(ulx, uly), # upper left
            QgsPoint(ulx + GT[1], uly), # upper right
            QgsPoint(ulx + GT[1], uly + GT[5]), # lower right
            QgsPoint(ulx, uly + GT[5])]] ) # lower left

        if setting.canvas['click_layer_id'] is not None:
            print 'Updating click layer geometry'
            ### If exists, update to new row/column
            vlayer = reg.mapLayers()[setting.canvas['click_layer_id']]
            vlayer.startEditing()
            pr = vlayer.dataProvider()
            attrs = pr.attributeIndexes()
            pr.select(attrs)
            feat = QgsFeature()
            while pr.nextFeature(feat):
                vlayer.changeAttributeValue(feat.id(), 0, py)
                vlayer.changeAttributeValue(feat.id(), 1, px)
                vlayer.changeGeometry(feat.id(), gSquare)
                vlayer.updateExtents()
            vlayer.commitChanges()
            vlayer.triggerRepaint()
        else:
            print 'Creating new vector to show click'
            ### Create layer since we removed it
            uri = QString('polygon?crs=%s' % self.ts.projection)
            vlayer = QgsVectorLayer(uri, 'Query', 'memory')
            pr = vlayer.dataProvider()
            vlayer.startEditing()
            pr.addAttributes( [ QgsField('row', QVariant.Int),
                               QgsField('col', QVariant.Int)])
            feat = QgsFeature()
            feat.setGeometry(gSquare)
            vlayer.updateExtents()
            feat.setAttributeMap( { 0: QVariant(px),
                                    1: QVariant(py) } )
            pr.addFeatures([feat])
            ### Do symbology
            # Reference:
            # http://lists.osgeo.org/pipermail/qgis-developer/2011-April/013772.html
            props = { 'color_border' : '255, 0, 0, 255', 
                     'style' : 'no',
                     'style_border' : 'solid',
                     'width' : '0.40' }
            s = QgsFillSymbolV2.createSimple(props)
            vlayer.setRendererV2(QgsSingleSymbolRendererV2(s))
    
            # Commit
            vlayer.commitChanges()
            # Add to map! (without emitting signal)
            vlayer_id = QgsMapLayerRegistry.instance().addMapLayer(vlayer).id()
            if vlayer_id:
                setting.canvas['click_layer_id'] = vlayer_id
    
        ### Set old layer selected
        self.iface.setActiveLayer(last_selected)

    ### Image table slots
    def get_tablerow_clicked(self, item):
        """
        If user clicks checkbox for image in image table, will add/remove
        image layer from map layers.
        """
        if item.column() != 0:
            return
        if item.checkState() == Qt.Checked:
            self.add_map_layer(item.row())
        elif item.checkState() == Qt.Unchecked:
            # If added is true and we now have unchecked, remove
            for layer in setting.image_layers:
                if self.ts.stacks[item.row()] == layer.source():
                    QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def add_map_layer(self, index):
        """
        Method called when adding an image via the table or plot.
        """
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
            self.apply_symbology(rlayer)
        # If we have already added it, move it to top
        elif any(add[0] for add in added):
            print 'Have added layer, moving to top!'
            index = [i for i, tup in enumerate(added) if tup[0] == True][0]
            self.move_layer_top(added[index][1].id())
        
        
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
            self.move_layer_top(setting.canvas['click_layer_id'])

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
            rows_removed = [row for row, (image_id, fname) in 
                enumerate(itertools.izip(self.ts.image_ids, self.ts.files))
                if image_id in layer_id or fname in layer_id]
            print 'Removed these rows %s' % str(rows_removed)
            for row in rows_removed:
                item = self.ctrl.image_table.item(row, 0)
                if item:
                    if item.checkState() == Qt.Checked:
                        item.setCheckState(Qt.Unchecked)

            if setting.canvas['click_layer_id'] == layer_id:
                print 'Removed click layer'
                print setting.canvas['click_layer_id']
                setting.canvas['click_layer_id'] = None

        # Sync setting.image_layers
        map_layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer_id in setting.image_layers:
            if layer_id not in map_layers:
                setting.image_layers.remove(layer_id)

    def move_layer_top(self, layer_id):
        """
        Move layer to top of map renderer set of layers so it appears in legend
        above all others and will render on top of others
        """
        # Some reference about mapRenderer and setLayerSet:
        # http://www.qgis.org/pyqgis-cookbook/composer.html
        canvas = self.iface.mapCanvas()
        renderer = canvas.mapRenderer()

        # Convert returned QStringList to list of QString and map to str
        layer_set = map(str, list(renderer.layerSet()))
        # Check if new layer is in list (i.e. only act if layer is on)
        if layer_id in layer_set:
            # Shuffle layer to top of layer_set
            layer_set.insert(0, layer_set.pop(layer_set.index(layer_id)))
            # Assign this newly ordered set to map renderer
            renderer.setLayerSet(QStringList(map(QString, layer_set)))
            # Force a refresh
            canvas.refresh()

    def disconnect(self):
        """
        Disconnect all signals added to various components
        """
        print 'TODO'
