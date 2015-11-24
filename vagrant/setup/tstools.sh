#!/bin/bash

# install TSTools
git clone https://github.com/ceholden/TSTools.git
cd TSTools/
sudo pip install -r requirements.txt
./deploy.sh

cd

# install example data
git clone https://github.com/ceholden/landsat_stack.git
cd landsat_stack/
tar -xjf p035r032.tar.bz2
