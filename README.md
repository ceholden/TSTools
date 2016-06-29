Time Series Tools (TSTools)
--------------------------

[![Join the chat at https://gitter.im/ceholden/TSTools](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/ceholden/TSTools?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) [![DOI](https://zenodo.org/badge/6804/ceholden/TSTools.svg)](https://zenodo.org/badge/latestdoi/6804/ceholden/TSTools)

## About
TSTools is a plugin for QGIS (version 2.4+) that helps visualize remote sensing time series by linking time series dataset models (objects that describe and characterize the time series) with user interface tools designed to harmonize the spatial and temporal dimensions of these large datasets.

[Read the Quickstart to see the plugin in action](docs/quickstart.md)

If you feel like TSTools has made a contribution to your research, please consider citing it using the plugin using the Digital Object Identifier (DOI) tracked by [Zenodo](https://zenodo.org/):

[![TSTools](https://zenodo.org/badge/6804/ceholden/TSTools.svg)](https://zenodo.org/badge/latestdoi/6804/ceholden/TSTools)

## Example data
An example dataset for this plugin is located here: https://github.com/ceholden/landsat_stack

## Installation
This plugin has not been uploaded to the main QGIS plugin repository so installation will need to be done manually. Please make sure you have the [required dependencies](#requirements)

### Users
One of the easiest ways to install TSTools, if you have the required dependencies, is to manually copy a "compiled" copy of the plugin into your QGIS plugins folder.

In most cases, the QGIS Python plugins folder will be located in your home directory within the ".qgis2/python/plugins" folder. Any plugins you have installed previously will be located here. For more information, see this excellent answer on [Stack Exchange](http://gis.stackexchange.com/questions/26979/how-to-install-a-qgis-plugin-when-offline).

1. Install QGIS and the required Python libraries (see requirements section below)
2. Download the file "tstools.zip" from a [release of TSTools on Github](https://github.com/ceholden/TSTools/releases).
3. Unzip the ZIP file to find the "tstools" folder.
4. Copy this "tstools" folder into your QGIS Python plugins directory (see above for where this is located)

To enable the plugin, continue following the [instructions for enabling the plugin](#enable).

### Developers
For anyone interested in developing the plugin or for those working in *nix environments, the easiest way to install the plugin is to clone this repository via `git` and to compile and deploy the plugin:

```
git clone https://github.com/ceholden/TSTools.git
cd TSTools/tstools/
make derase
make clean
make
make deploy
```

To enable the plugin, continue following the [instructions for enabling the plugin](#enable).

### Vagrant

A remarkably easy way of quickly installing and using `TSTools` is to utilize the included setup script for the [Vagrant](https://www.vagrantup.com/) technology. [Vagrant](https://www.vagrantup.com/) enables users to quickly and reproducibly configure and create lightweight virtual machines. I have included a `Vagrantfile` inside `vagrant/` that sets up a Ubuntu "Xenial Xerus" 16.04 Linux virtual machine with TSTools and all pre-requisites installed.

To run TSTools using Vagrant, install Vagrant for your platform from [their downloads page](http://www.vagrantup.com/downloads):

http://www.vagrantup.com/downloads

Installation instructions are [available here](https://docs.vagrantup.com/v2/installation/index.html).

You will also need software to run the virtual machine, or a "provider" as Vagrant calls it. I recommend [VirtualBox](https://www.virtualbox.org/wiki/Downloads) because it works well, is cross-platform, and is free and open-source. More providers and instructions for using these providers is available [on Vagrant's documentation page](https://docs.vagrantup.com/v2/providers/index.html).

Once you have Vagrant and a provider installed, you can run the Vagrant machine as follows:

``` bash
# Navigate into the folder and vagrant up!
cd vagrant/
vagrant up
```

Once the virtual machine has been downloaded, configured, and provisioned, you can connect to it and launch QGIS via SSH:

``` bash
vagrant ssh
qgis
```

That's it! You can `suspend`, `halt`, or `destroy` (delete) the virtual machine when you're done using these as the `<command>` in `vagrant <command>`.

For more information about Vagrant and how to use the technology, check out their ["Getting Started"](https://docs.vagrantup.com/v2/getting-started/index.html) section within [their documentation page](https://docs.vagrantup.com/v2/).

## Enable
Once TSTools is installed, follow these steps to enable it:

1. Launch QGIS and open the Plugin Manage dialog (Plugins menu -> Manage and Install Plugins)
2. Check the box next to "TSTools" to enable the plugin

Two new icons will be added to the plugins toolbar. These icons have the letters "TS" in capital red colored letters. To initialize a timeseries dataset within the plugin, click the icon without the crosshair symbol. Point this dialog to your timeseries and configure any additional options before clicking "Okay". To retrieve the timeseries for any given pixel, add an image from your timeseries to QGIS using the "Images" tab and click the "TS" icon with the crosshairs to replace your current map tool with the "TSTools" map tool.

## Requirements

As this is a QGIS plugin, QGIS, GDAL, and Python 2.7+ are, of course, required. Most, if not all, installations of QGIS also provide a copy of `numpy` and `matplotlib` so most users should be able to use TSTools "out of the box".

### Python dependencies:

    matplotlib>=1.4.0
    numpy>=1.8.0
    GDAL>=1.10.0

### Optional dependencies:

The following are additional, optional dependencies:

    palettable>=2.1.1
    scandir

The `palettable` package provides better colormap support for the plots. `scandir` speeds up the process of the plugin finding timeseries data spread across many files and directories. `markdown2` enables stylistic parsing of timeseries driver information formatted in Markdown.

### Timeseries driver dependencies:

* `CCDC Results Reader`
    - For reading Continuous Change Detection and Classification (CCDC) results:
        + `scipy>=0.12.0`
* `YATSM CCDCesuqe Timeseries`, and other `YATSM *` drivers
    - For live plotting with YATSM (including CCDC-esque clone), you need to install the `YATSM` package. See instructions at the following repository location:
        + [https://github.com/ceholden/yatsm](https://github.com/ceholden/yatsm)

### Developer dependencies:
To help develop this plugin, you will need QGIS, Python, and the Qt developer tools for Python (for building). The Qt dependencies are available on Ubuntu in the `pyqt4-dev-tools` package.
