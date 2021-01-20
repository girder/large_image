#!/bin/bash

set -e

ROOTPATH=`pwd`

export SETUPTOOLS_SCM_PRETEND_VERSION=`python -m setuptools_scm | sed "s/.* //"`
if [ ${CIRCLE_BRANCH-:} = "master" ]; then export SETUPTOOLS_SCM_PRETEND_VERSION=`echo $SETUPTOOLS_SCM_PRETEND_VERSION | sed "s/\+.*$//"`; fi

python setup.py sdist
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/girder"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/girder_annotation"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/utilities/converter"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/utilities/tasks"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/bioformats"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/dummy"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/gdal"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/mapnik"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/nd2"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/ometiff"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/openjpeg"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/openslide"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/pil"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/test"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*
cd "$ROOTPATH/sources/tiff"
python setup.py sdist
cp "$ROOTPATH/README.rst" .
pip wheel . --no-deps -w dist
twine upload --verbose dist/*

