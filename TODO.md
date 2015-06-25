# TODO

1. [x] When we initialize a timeseries with a custom config, if we get an AttributeError then make sure to pass it on to user as a QgsMessageBar error
2. [x] Implement "Series" class that holds a `type (str)`, `images (np.recarray)`, `band_names (list)`, `symbology (list)`, and `metadata`. This adds an extra layer of abstraction separating the timeseries driver from the data to allow for multiple types of timeseries (e.g., ALOS and Landsat) within one driver.
3. [x] Add QComboBox for symbology and images table that controls top layer of QStackedWidget. This should allow for each timeseries driver to have multiple series that are controlled independently.
4. [x] Move elements UI of symbology tab (and images table? probably not complicated enough since we don't really need to draw the UI... just create and populate the table) into separate UI files. Add a new instance of each element to each tab's QStackedWidget for every `Series` contained in the timeseries driver.
5. [x] Redo plot controls tab to concatenate `band_names` from each `Series` in a given timeseries driver. Keep track of the index of the `Series` and the index of the band within each `Series` for each QComboBox item.
    + We keep track of raveled / unraveled `[series][bands]` using following variables in `settings`
        * `plot_series`
        * `plot_band_indices`
        * `plot_bands`
6. [ ] Implement caching into `timeseries_stacked`
7. [ ] Probably need to expose `_GDALStackReader` class in `reader`. Would be useful when reading multiple timeseries (e.g., MODIS and Landsat, or Landsat and ALOS)
8. [ ] Try to implement caching as a decorator? Generic TS tools as decorators?
9. [ ] DOY plot
10. [ ] Configuration / settings control panel that joins into persistent settings storage with `QSettings` [here](http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/settings.html) (issue #51)
11. [ ] Fix bug with plot -- seems to only plot some of the predicted line first time it plots. Fixed on a replot of the data
98. [ ] Remove exception raised in `controller` (see #TODO tag)
99. [ ] Search for and resolve `TODO:HARDCODE` tags
