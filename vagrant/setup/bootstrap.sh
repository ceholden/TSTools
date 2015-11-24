#!/bin/bash

if [ -f ~/.bootstrap_complete ]; then
    exit 0
fi

set -x

# do all system updates
sudo apt-get update -y

# force upgrade of packages and force it to not be interactive
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade

# install add-apt-repository script
sudo apt-get install python-software-properties -y

# add Ubuntu GIS repo (for some reason it needs a full path)
sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y

# force updates with new repo
sudo apt-get update -y
sudo apt-get dist-upgrade -y

# install tools & dependencies
sudo apt-get install -y build-essential \
    curl git vim zip bzip2 \
    python-dev python-setuptools python-pip \
    python-virtualenv virtualenvwrapper \
    pyqt4-dev-tools \
    gdal-bin libgdal-dev

# dependencies for matplotlib
sudo apt-get build-dep -y python-matplotlib

set +e

# install QGIS
sudo apt-get install qgis -y

touch ~/.bootstrap_complete
