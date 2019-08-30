#!/bin/bash

path=$1
if [ -z "$path" ]; then
	echo "You need to specify path."
	exit 1;
fi
cd $path
mkdir indexed

for img in *.png; do
	file=$(basename "$img")
	convert -dither FloydSteinberg -colors 256 "$img" "indexed/$file"
done
cd -
echo "Images indexed."
