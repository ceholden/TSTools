Time Series Tools (TSTools)
-------------------

### About
TSTools is a plugin for QGIS (version 2.0+) that helps visualize remote sensing time series by linking time series dataset models (objects that describe and characterize the time series) with user interface tools designed to harmonize the spatial and temporal dimensions of these large datasets.

While this QGIS plugin was originally designed for use with the "Continuous Change Detection and Classification" algorithm (Zhu and Woodcock 2014), I am working (slowly) to make the backend code and user interface extensible for use with any number of time series algorithms.

The goal is for users to describe their own data set structures, algorithm parameters, and algorithm outputs and then plug these customizations into the TSTools plugin by inheriting from the abstract base class "TimeSeries". This base class acts as an interface descriptor that characterizes what methods and properties are required for use within the user interface.

### Installation
This plugin has not been uploaded to the main QGIS plugin repository so installation will need to be done manually.

In most cases, the QGIS Python plugins folder will be located in your home directory within the ".qgis2/python/plugins" folder. Any plugins you have installed previously will be located here. For more information, see this excellent answer on [Stack Exchange](http://gis.stackexchange.com/questions/26979/how-to-install-a-qgis-plugin-when-offline).

Steps:
1. Download the file "tstools.zip" from this repository on Github.
2. Unzip the ZIP file to find the "tstools" folder.
3. Copy this "tstools" folder into your QGIS Python plugins directory (see above for where this is located)
4. Launch QGIS and open the Plugin Manage dialog (Plugins menu -> Manage and Install Plugins)
5. Check the box next to "TSTools" to enable the plugin

Two new icons will be added to the plugins toolbar. These icons have the letters "TS" in capital red colored letters. To initialize a timeseries dataset within the plugin, click the icon without the crosshair symbol. Point this dialog to your timeseries and configure any additional options before clicking "Okay". To retrieve the timeseries for any given pixel, add an image from your timeseries to QGIS using the "Images" tab and click the "TS" icon with the crosshairs to replace your current map tool with the "TSTools" map tool.

An example dataset for this plugin is located here:
https://github.com/ceholden/landsat_stack

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
