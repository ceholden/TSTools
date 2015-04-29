#!/bin/bash

if [ ! -d i18n ]; then
	mkdir i18n
fi

set -e

if [ -d src/yatsm ]; then
    here=$(pwd)
    cd src/yatsm
    python setup.py build_ext --inplace
    cd $here
fi

make
make clean
make derase
make deploy
make zip
