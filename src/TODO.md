# TODO

1. When we initialize a timeseries with a custom config, if we get an AttributeError then make sure to pass it on to user as a QgsMessageBar error
2. Ignore plot views for now; prioritize controller and communication with `tsm.ts`
3. Probably don't need `actors` file. 
4. Implement caching into `timeseries_stacked`
5. Probably need to expose `_GDALStackReader` class in `reader`. Would be useful when reading multiple timeseries (e.g., MODIS and Landsat, or Landsat and ALOS)
6. Search for and resolve `TODO:HARDCODE` tags
100. TODO more TODO
