#!/bin/bash

set -e

ROOTPATH=`pwd`

python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/girder"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/girder_annotation"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/tasks"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/dummy"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/mapnik"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/openslide"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/pil"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/test"
python setup.py sdist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/tiff"
python setup.py sdist
twine upload --verbose dist/*

