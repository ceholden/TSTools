#!/bin/bash

cd $(dirname $0)/tstools/

if [ ! -d i18n ]; then
	mkdir i18n
fi

set -e

make
make clean
make derase
make deploy
make zip
