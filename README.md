Timeseries Tools (TSTools)
--------------------------

## About
TSTools is a plugin for QGIS (version 2.0+) that helps visualize remote sensing time series by linking time series dataset models (objects that describe and characterize the time series) with user interface tools designed to harmonize the spatial and temporal dimensions of these large datasets.

[Read the Quickstart to see the plugin in action](docs/quickstart.md)

## Example data
An example dataset for this plugin is located here:
https://github.com/ceholden/landsat_stack

## Installation
This plugin has not been uploaded to the main QGIS plugin repository so installation will need to be done manually.

### Users
One of the easiest ways to install TSTools is to manually copy a "compiled" copy of the plugin into your QGIS plugins folder.

In most cases, the QGIS Python plugins folder will be located in your home directory within the ".qgis2/python/plugins" folder. Any plugins you have installed previously will be located here. For more information, see this excellent answer on [Stack Exchange](http://gis.stackexchange.com/questions/26979/how-to-install-a-qgis-plugin-when-offline).

1. Install QGIS and the required Python libraries (see requirements section below)
2. Download the file "tstools.zip" from this repository on Github.
3. Unzip the ZIP file to find the "tstools" folder.
4. Copy this "tstools" folder into your QGIS Python plugins directory (see above for where this is located)

To enable the plugin, continue following the [instructions for enabling the plugin](#enable).

### Developers
For anyone interested in developing the plugin or for those working in *nix environments, the easiest way to install the plugin is to clone this repository via `git` and to compile and deploy the plugin:

```
git clone https://github.com/ceholden/TSTools.git
cd TSTools/
make derase
make clean
make
make deploy
```

To enable the plugin, continue following the [instructions for enabling the plugin](#enable).

### Enable
Once TSTools is installed, follow these steps to enable it:
1. Launch QGIS and open the Plugin Manage dialog (Plugins menu -> Manage and Install Plugins)
2. Check the box next to "TSTools" to enable the plugin

Two new icons will be added to the plugins toolbar. These icons have the letters "TS" in capital red colored letters. To initialize a timeseries dataset within the plugin, click the icon without the crosshair symbol. Point this dialog to your timeseries and configure any additional options before clicking "Okay". To retrieve the timeseries for any given pixel, add an image from your timeseries to QGIS using the "Images" tab and click the "TS" icon with the crosshairs to replace your current map tool with the "TSTools" map tool.

### Virtual machine demo
To help out people who find the installation of this software is not so straightforward (e.g., it is more difficult on Windows than Linux), I have created a virtual machine of the 14.04 LTS [Ubuntu Mate distribution](https://ubuntu-mate.org/) with everything installed. This virtual machine contains a full stack of softwares - GDAL, Python, QGIS, NumPy, SciPy, etc. - that are required to use the plugin. The virtual machine is formatted as a [VirtualBox image](https://www.virtualbox.org/) and I would recommend you to use [VirtualBox](https://www.virtualbox.org/) to run the virtual machine. VirtualBox is a free and open source softare that can create and host virtual machines and is comparable to commercial solutions such as VMWare or Parallels.

The virtual machine has been exported to a [VirtualBox appliance](http://www.virtualbox.org/manual/ch01.html#ovf) and uploaded to my university department's anonymous FTP server:

[ftp://ftp-earth.bu.edu/ceholden/VM/](ftp://ftp-earth.bu.edu/ceholden/VM/)

Please see the included README for further instructions. A md5sum of the virtual disk appliance is provided for confirming the file transfer integrity.

## Requirements
### Main dependencies:

    Python>=2.7.5
    Matplotlib>=1.4.0
    Numpy>=1.8.0
    GDAL>=1.10.0
    palettable>=2.1.1
    
### Additional dependencies:

- For reading Continuous Change Detection and Classification (CCDC) results:
    + `scipy>=0.12.0`
- For live plotting with YATSM (including CCDC-esque clone):
    + see [https://github.com/ceholden/yatsm](https://github.com/ceholden/yatsm)

### Developer dependencies:
To help develop this plugin, you will need QGIS, Python, and the Qt developer tools for Python (for building). The Qt dependencies are available on Ubuntu in the "pyqt4-dev-tools" package.
