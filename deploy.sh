#!/bin/bash

if [ ! -d i18n ]; then
	mkdir i18n
fi

set -e

make
make clean
make derase
make deploy
make zip
