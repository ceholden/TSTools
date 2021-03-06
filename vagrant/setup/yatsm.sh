#!/bin/bash

# Install latest release of YATSM
git clone https://github.com/ceholden/yatsm.git
cd yatsm/
latest_tag=$(git describe --tags $(git rev-list --tags --max-count=1))
git checkout $latest_tag

# Help out requirements with Ubuntu packages
sudo apt-get install -y \
    cython \
    python-scipy \
    python-scikits-learn \
    python-statsmodels \
    python-pandas \
    python-yaml \
    python-matplotlib \
    python-rpy2 \
    r-base

# PIP requirements
sudo pip install -r requirements.txt
sudo pip install -r requirements/pheno.txt
sudo pip install .
