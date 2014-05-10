Time Series Tools (TSTools)
-------------------

### About
TSTools is a plugin for QGIS (version 2.0+) that helps visualize remote sensing time series by linking time series dataset models (objects that describe and characterize the time series) with user interface tools designed to harmonize the spatial and temporal dimensions of these large datasets.

While this QGIS plugin was originally designed for use with the "Continuous Change Detection and Classification" algorithm (Zhu and Woodcock 2014), I am working (slowly) to make the backend code and user interface extensible for use with any number of time series algorithms.

The goal is for users to describe their own data set structures, algorithm parameters, and algorithm outputs and then plug these customizations into the TSTools plugin by inheriting from the abstract base class "TimeSeries". This base class acts as an interface descriptor that characterizes what methods and properties are required for use within the user interface.

### Features
##### Plot time series and time series model fits by clicking on image
<img src="https://raw.githubusercontent.com/ceholden/TSTools/master/docs/media/beetle_ts_2013.png" align="center" width=500/>

*Time series fit from Zhe Zhu's CCDC*

##### Plot features
+ Click a plot point and open corresponding image in QGIS
+ Adjust X and Y plot limits
+ Turn on or off model results
+ Export image as PNG, EPS, etc.

##### Quickly add/remove time series images from table
<img src="https://raw.githubusercontent.com/ceholden/TSTools/master/docs/media/tstools_imagetable.png" align="center" width=250/>

*Metadata columns coming soon*

##### Control image symbology for all time series images
<img src="https://raw.githubusercontent.com/ceholden/TSTools/master/docs/media/tstools_symbology.png" align="center" width=250/>

##### Add your own time series model with custom initialization requirements
<img src="https://raw.githubusercontent.com/ceholden/TSTools/master/docs/media/tstools_customconfig.png" align="center" width=250/>
