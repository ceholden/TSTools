#!/bin/bash

if [ ! -d i18n ]; then
	mkdir i18n
fi

set -e

# Patch out Cython in YATSM if it exists
yatsm=src/yatsm/yatsm/yatsm.py
if [ -f $yatsm ]; then
    sed -i 's|from cyatsm import|#from cyatsm import|g' $yatsm
    sed -i 's|cymultitemp_mask|multitemp_mask|g' $yatsm
fi

make
make clean
make derase
make deploy
make zip
