#!/bin/bash

if [ -z $1 ]; then
    echo "Must provide root of TSTools/src as 1st arg"
    exit 1
fi
if [ -z $2 ]; then
    out=TSTools_Graph.pdf
else
    out=$2
fi

sfood -i $1 | sfood-cluster | sfood-graph > $(basename $out .pdf).dot
sfood -i $1 | sfood-cluster | sfood-graph | dot -Tps | ps2pdf - $out
