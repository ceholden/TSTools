#!/bin/bash

if [ ! -d i18n ]; then
	mkdir i18n
fi

make clean
make
make clean
make derase
make deploy
make zip
