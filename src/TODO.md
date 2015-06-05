# TODO

1. [ ] When we initialize a timeseries with a custom config, if we get an AttributeError then make sure to pass it on to user as a QgsMessageBar error
2. [ ] Ignore plot views for now; prioritize controller and communication with `tsm.ts`
3. [ ] Implement "Series" class that holds a `type (str)`, `images (np.recarray)`, `band_names (list)`, `symbology (list)`, and `metadata`. This adds an extra layer of abstraction separating the timeseries driver from the data to allow for multiple types of timeseries (e.g., ALOS and Landsat) within one driver.
4. [ ] Add QComboBox for symbology and images table that controls top layer of QStackedWidget. This should allow for each timeseries driver to have multiple series that are controlled independently.
5. [ ] Move elements UI of symbology tab (and images table? probably not complicated enough since we don't really need to draw the UI... just create and populate the table) into separate UI files. Add a new instance of each element to each tab's QStackedWidget for every `Series` contained in the timeseries driver.
6. [ ] Redo plot controls tab to concatenate `band_names` from each `Series` in a given timeseries driver. Keep track of the index of the `Series` and the index of the band within each `Series` for each QComboBox item.
7. [ ] `settings` will need multiple `symbol (dict)` containers per `Series` contained within QStackedWidget. `settings` will also need a tracker for which `Series` is displayed within the QStackedWidget (e.g., `series_table` and `series_symbol` $$\in{[0, 1]}$$)
10. [ ] Implement caching into `timeseries_stacked`
11. [ ] Probably need to expose `_GDALStackReader` class in `reader`. Would be useful when reading multiple timeseries (e.g., MODIS and Landsat, or Landsat and ALOS)
99. [ ] Search for and resolve `TODO:HARDCODE` tags
100. [ ] TODO more TODO
